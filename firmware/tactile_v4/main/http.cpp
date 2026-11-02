#include "http.hpp"
#ifdef V4_HTTP_NATIVE
#include "http_native_stubs.hpp"
#else
#include "app.hpp"
#include "storage.hpp"
#include "web/web_assets.hpp"
#include "freertos/semphr.h"
#include "esp_http_server.h"
#include "esp_timer.h"
#include "esp_err.h"
#include "esp_attr.h"
#include "lwip/sockets.h"
#endif
#include "core.hpp"
#include <atomic>
#include <cerrno>
#include <cstdio>
#include <cstring>

namespace {
httpd_handle_t server=nullptr;
QueueHandle_t browserFrames=nullptr;
SemaphoreHandle_t videoMutex=nullptr;
VideoFrame* latestVideo=nullptr;
std::atomic<bool> ready{false},workPending{false};
std::atomic<int> browserFd{-1};
std::atomic<uint32_t> browserDrops{0},browserVideoDrops{0};
uint32_t browserSequence=0; // Producers hold the shared packet mutex.
bool latestClaimed=false; // Protected by videoMutex; an in-flight frame owns its reference.
uint64_t sendDeadline=0; // Used only by the HTTP server task.

// IDF's WS send routine calls send_fn once for each header/payload. Complete
// partial socket writes here, with one shared deadline for the entire frame.
int boundedSend(httpd_handle_t,int fd,const char* bytes,size_t size,int flags){
 const uint64_t deadline=sendDeadline?sendDeadline:uint64_t(esp_timer_get_time())+200000;
 size_t done=0;
 while(done<size){
  if(uint64_t(esp_timer_get_time())>=deadline)return HTTPD_SOCK_ERR_TIMEOUT;
  int n=send(fd,bytes+done,size-done,flags|MSG_DONTWAIT);
  if(n>0)done+=size_t(n);
  else if(n<0&&(errno==EAGAIN||errno==EWOULDBLOCK||errno==EINTR))vTaskDelay(1);
  else return HTTPD_SOCK_ERR_FAIL;
 }
 return int(done);
}
bool sendBinary(int fd,uint8_t*bytes,size_t size){
 httpd_ws_frame_t frame{};frame.type=HTTPD_WS_TYPE_BINARY;frame.payload=bytes;frame.len=size;
 sendDeadline=uint64_t(esp_timer_get_time())+200000;
 bool ok=httpd_ws_send_frame_async(server,fd,&frame)==ESP_OK;
 sendDeadline=0;return ok;
}
void clearLatest(){
 xSemaphoreTake(videoMutex,portMAX_DELAY);VideoFrame*old=latestVideo;latestVideo=nullptr;if(old&&!latestClaimed)browserVideoDrops++;latestClaimed=false;xSemaphoreGive(videoMutex);
 if(old)releaseVideo(old);
}
void discardPackets(){
 xSemaphoreTake(videoMutex,portMAX_DELAY);Packet p;while(xQueueReceive(browserFrames,&p,0)==pdTRUE)browserDrops++;xSemaphoreGive(videoMutex);
}
void closeSession(httpd_handle_t,int fd){
 int expected=fd;
 if(browserFd.compare_exchange_strong(expected,-1)){discardPackets();clearLatest();}
 close(fd); // A custom close_fn owns the actual socket close in ESP-IDF.
}
void failSession(int fd){
 int expected=fd;browserFd.compare_exchange_strong(expected,-1);
 discardPackets();clearLatest();
 httpd_sess_trigger_close(server,fd);
}
void sendWork(void*){
 const int fd=browserFd.load();
 if(fd<0||httpd_ws_get_fd_info(server,fd)!=HTTPD_WS_CLIENT_WEBSOCKET){workPending=false;return;}
 Packet p{};bool ok=true;
 for(unsigned i=0;i<8&&xQueueReceive(browserFrames,&p,0)==pdTRUE;i++){
  uint8_t bytes[257];bytes[0]=0;memcpy(bytes+1,p.data,p.size);
  if(!sendBinary(fd,bytes,p.size+1)){browserDrops++;ok=false;break;}
 }
 if(ok){
  xSemaphoreTake(videoMutex,portMAX_DELAY);VideoFrame*f=latestClaimed?nullptr:latestVideo;if(f){f->refs++;latestClaimed=true;}xSemaphoreGive(videoMutex);
  if(f){ok=sendBinary(fd,f->storage,f->bytes+1);if(!ok)browserVideoDrops++;releaseVideo(f);}

 }
 if(!ok)failSession(fd);
 workPending=false;
}
void browserPump(void*){
 for(;;){
  if(browserFd.load()>=0&&!workPending.exchange(true)){
   if(httpd_queue_work(server,sendWork,nullptr)!=ESP_OK)workPending=false;
  }
  vTaskDelay(pdMS_TO_TICKS(10));
 }
}
bool sameOrigin(httpd_req_t*request){
 // Browser clients must originate at this cuff's own HTTP host. Native tools
 // may omit Origin; the WPA2 network key remains the access boundary.
 size_t n=httpd_req_get_hdr_value_len(request,"Origin");if(!n)return true;
 char origin[96],host[64],expected[80];
 if(n>=sizeof(origin)||httpd_req_get_hdr_value_str(request,"Origin",origin,sizeof(origin))!=ESP_OK)return false;
 if(httpd_req_get_hdr_value_str(request,"Host",host,sizeof(host))!=ESP_OK)return false;
 int length=snprintf(expected,sizeof(expected),"http://%s",host);
 return length>0&&size_t(length)<sizeof(expected)&&!strcmp(origin,expected);
}
esp_err_t websocket(httpd_req_t*request){
 int fd=httpd_req_to_sockfd(request);
 if(request->method==HTTP_GET){
  // IDF5.4 performs the upgrade before invoking this handler: return a
  // failure to close rejected sessions, rather than writing an HTTP response.
  if(!sameOrigin(request))return ESP_FAIL;
  if(browserFd.load()>=0&&browserFd.load()!=fd)return ESP_FAIL;
  discardPackets();clearLatest();
  if(httpd_sess_set_send_override(server,fd,boundedSend)!=ESP_OK)return ESP_FAIL;
  browserFd=fd;return ESP_OK;
 }
 httpd_ws_frame_t frame{};esp_err_t result=httpd_ws_recv_frame(request,&frame,0);
 if(result!=ESP_OK)return result;
 if(frame.type!=HTTPD_WS_TYPE_TEXT||!frame.final||!frame.len||frame.len>31)return ESP_FAIL;
 uint8_t bytes[32]{};frame.payload=bytes+1;
 if(httpd_ws_recv_frame(request,&frame,31)!=ESP_OK)return ESP_FAIL;
 if(V4::Command::parse(bytes+1,frame.len).kind==V4::Command::Invalid)return ESP_FAIL;
 bytes[0]=uint8_t(frame.len);
 return xQueueSend(commands,bytes,0)==pdTRUE?ESP_OK:ESP_FAIL;
}
esp_err_t asset(httpd_req_t*request){
 char path[160];size_t length=strcspn(request->uri,"?");
 if(length>=sizeof(path))return httpd_resp_send_err(request,HTTPD_404_NOT_FOUND,"Asset unavailable.");
 memcpy(path,request->uri,length);path[length]=0;
 for(size_t i=0;i<webAssetCount;i++)if(!strcmp(path,webAssets[i].path)){
  httpd_resp_set_type(request,webAssets[i].mime);
  httpd_resp_set_hdr(request,"Content-Encoding","gzip");
  httpd_resp_set_hdr(request,"Cache-Control","no-cache");
  httpd_resp_set_hdr(request,"X-Content-Type-Options","nosniff");
  return httpd_resp_send(request,reinterpret_cast<const char*>(webAssets[i].data),webAssets[i].size);
 }
 return httpd_resp_send_err(request,HTTPD_404_NOT_FOUND,"Asset unavailable.");
}
} // namespace

void queueBrowserPacket(uint8_t kind,uint64_t stamp,const uint8_t*payload,uint16_t bytes){
 if(kind==V4::KIND_SCAN||!ready.load()||browserFd.load()<0)return;
 xSemaphoreTake(videoMutex,portMAX_DELAY);
 if(browserFd.load()<0){xSemaphoreGive(videoMutex);return;}
 Packet p{};p.size=V4::encodePacket(kind,browserSequence++,stamp,payload,bytes,p.data);
 if(!p.size||xQueueSend(browserFrames,&p,0)!=pdTRUE)browserDrops++;
 xSemaphoreGive(videoMutex);
}
void publishBrowserVideo(VideoFrame*frame){
 if(!ready.load()||browserFd.load()<0)return;
 xSemaphoreTake(videoMutex,portMAX_DELAY);
 // Recheck under the same lock used by closeSession: a camera publish that
 // raced with disconnect must not leave an unused frame retained.
 if(browserFd.load()<0){xSemaphoreGive(videoMutex);return;}
 frame->refs++;VideoFrame*old=latestVideo;if(old&&!latestClaimed)browserVideoDrops++;latestVideo=frame;latestClaimed=false;xSemaphoreGive(videoMutex);
 if(old)releaseVideo(old);
}
void beginBrowser(){
 browserFrames=createPacketQueue(64);videoMutex=xSemaphoreCreateMutex();assert(browserFrames&&videoMutex);
 httpd_config_t cfg=HTTPD_DEFAULT_CONFIG();cfg.server_port=80;cfg.core_id=0;cfg.task_priority=6;cfg.stack_size=6144;cfg.max_open_sockets=4;cfg.max_uri_handlers=4;cfg.lru_purge_enable=true;cfg.send_wait_timeout=1;cfg.recv_wait_timeout=1;cfg.uri_match_fn=httpd_uri_match_wildcard;cfg.close_fn=closeSession;
 ESP_ERROR_CHECK(httpd_start(&server,&cfg));
 httpd_uri_t ws{};ws.uri="/ws";ws.method=HTTP_GET;ws.handler=websocket;ws.is_websocket=true;
 ESP_ERROR_CHECK(httpd_register_uri_handler(server,&ws));
 httpd_uri_t files{};files.uri="/*";files.method=HTTP_GET;files.handler=asset;
 ESP_ERROR_CHECK(httpd_register_uri_handler(server,&files));
 ready=true;createCheckedTask(browserPump,"browser-pump",3072,nullptr,5,nullptr,0);
}

void browserStatus(uint8_t payload[8]){V4::put32(payload,browserDrops.load());V4::put32(payload+4,browserVideoDrops.load());}
