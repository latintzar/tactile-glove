#pragma once
// Instrumented platform boundary for the exact HTTP implementation. These
// stubs test routing/lifetimes/deadlines; they do not model Wi-Fi or IDF timing.
#include "../../firmware/tactile_v4/main/packet.hpp"
#include "../../firmware/tactile_v4/main/video_frame.hpp"
#include "../../firmware/tactile_v4/main/web/web_assets.hpp"
#include <cassert>
#include <cstring>
#include <deque>
#include <map>
#include <mutex>
#include <string>
#include <vector>
#include <cerrno>
using esp_err_t=int;using BaseType_t=int;using UBaseType_t=unsigned;using TaskHandle_t=void*;using TaskFunction_t=void(*)(void*);
constexpr int ESP_OK=0,ESP_FAIL=-1,HTTP_GET=1,HTTPD_WS_TYPE_TEXT=1,HTTPD_WS_TYPE_BINARY=2,HTTPD_WS_CLIENT_WEBSOCKET=3,HTTPD_404_NOT_FOUND=404,HTTPD_SOCK_ERR_TIMEOUT=-2,HTTPD_SOCK_ERR_FAIL=-3,HTTPD_RESP_USE_STRLEN=-1,MSG_DONTWAIT=1,pdTRUE=1,portMAX_DELAY=-1;
#define pdMS_TO_TICKS(x) (x)
#define ESP_ERROR_CHECK(x) assert((x)==ESP_OK)
struct NativeQueue {size_t cap,bytes;std::deque<std::vector<uint8_t>> items;};using QueueHandle_t=NativeQueue*;using SemaphoreHandle_t=std::mutex*;
inline QueueHandle_t createPacketQueue(unsigned n){return new NativeQueue{n,sizeof(Packet),{}};}
inline int xQueueSend(QueueHandle_t q,const void*p,int){if(q->items.size()==q->cap)return 0;auto*b=(const uint8_t*)p;q->items.emplace_back(b,b+q->bytes);return 1;}
inline int xQueueReceive(QueueHandle_t q,void*p,int){if(q->items.empty())return 0;memcpy(p,q->items.front().data(),q->bytes);q->items.pop_front();return 1;}
inline void xQueueReset(QueueHandle_t q){q->items.clear();}
inline SemaphoreHandle_t xSemaphoreCreateMutex(){return new std::mutex;}
inline void xSemaphoreTake(SemaphoreHandle_t m,int){m->lock();}
inline void xSemaphoreGive(SemaphoreHandle_t m){m->unlock();}
inline uint64_t nativeTime=0;inline int64_t esp_timer_get_time(){return nativeTime;}
inline void vTaskDelay(int ticks){nativeTime+=ticks*1000;}
inline BaseType_t createCheckedTask(TaskFunction_t,const char*,uint32_t,void*,UBaseType_t,TaskHandle_t*,BaseType_t){return 1;}
inline QueueHandle_t commands=new NativeQueue{8,32,{}};
inline unsigned freedVideos=0;
inline void releaseVideo(VideoFrame*f){if(f->refs.fetch_sub(1)==1){delete[] f->storage;delete f;freedVideos++;}}
using httpd_handle_t=void*;
struct httpd_req_t {httpd_handle_t handle=nullptr;int method=HTTP_GET,fd=5;const char*uri="/";std::map<std::string,std::string> headers,responseHeaders;std::vector<uint8_t> incoming,response;int incomingType=HTTPD_WS_TYPE_TEXT,status=200;bool incomingFinal=true;std::string mime;};
struct httpd_ws_frame_t {int type=0;uint8_t*payload=nullptr;size_t len=0;bool final=false;};
using NativeSend=int(*)(httpd_handle_t,int,const char*,size_t,int);
struct httpd_config_t {int server_port=0,core_id=0,task_priority=0,stack_size=0,max_open_sockets=0,max_uri_handlers=0,send_wait_timeout=0,recv_wait_timeout=0;bool lru_purge_enable=false;void*uri_match_fn=nullptr;void(*close_fn)(httpd_handle_t,int)=nullptr;};
#define HTTPD_DEFAULT_CONFIG() httpd_config_t{}
inline void*httpd_uri_match_wildcard=nullptr;
struct httpd_uri_t {const char*uri=nullptr;int method=0;esp_err_t(*handler)(httpd_req_t*)=nullptr;bool is_websocket=false;};
inline httpd_config_t nativeConfig;inline std::vector<httpd_uri_t> nativeRoutes;inline std::map<int,NativeSend> nativeSend;inline std::map<int,std::vector<uint8_t>> socketBytes;inline std::vector<std::vector<uint8_t>> sentPayloads;inline std::vector<int> closedSockets;inline bool socketBlocked=false,socketFailed=false;inline size_t socketChunk=7;
inline int send(int fd,const void*p,size_t n,int){nativeTime+=1;if(socketFailed){errno=ECONNRESET;return -1;}if(socketBlocked){errno=EAGAIN;return -1;}n=std::min(n,socketChunk);auto*b=(const uint8_t*)p;socketBytes[fd].insert(socketBytes[fd].end(),b,b+n);return int(n);}
inline int close(int fd){closedSockets.push_back(fd);return 0;}
inline int httpd_start(httpd_handle_t*h,httpd_config_t*c){nativeConfig=*c;*h=(void*)1;return ESP_OK;}
inline int httpd_register_uri_handler(httpd_handle_t,const httpd_uri_t*r){nativeRoutes.push_back(*r);return ESP_OK;}
inline int httpd_req_to_sockfd(httpd_req_t*r){return r->fd;}
inline int httpd_sess_set_send_override(httpd_handle_t,int fd,NativeSend f){nativeSend[fd]=f;return ESP_OK;}
inline int httpd_ws_get_fd_info(httpd_handle_t,int fd){return nativeSend.count(fd)?HTTPD_WS_CLIENT_WEBSOCKET:0;}
inline int httpd_sess_trigger_close(httpd_handle_t h,int fd){nativeSend.erase(fd);nativeConfig.close_fn(h,fd);return ESP_OK;}
inline int httpd_queue_work(httpd_handle_t,void(*f)(void*),void*arg){f(arg);return ESP_OK;}
inline size_t httpd_req_get_hdr_value_len(httpd_req_t*r,const char*k){return r->headers[k].size();}
inline int httpd_req_get_hdr_value_str(httpd_req_t*r,const char*k,char*out,size_t n){auto it=r->headers.find(k);if(it==r->headers.end()||it->second.size()>=n)return ESP_FAIL;strcpy(out,it->second.c_str());return ESP_OK;}
inline int httpd_ws_recv_frame(httpd_req_t*r,httpd_ws_frame_t*f,size_t n){f->type=r->incomingType;f->final=r->incomingFinal;f->len=r->incoming.size();if(!n)return ESP_OK;if(f->len>n)return ESP_FAIL;memcpy(f->payload,r->incoming.data(),f->len);return ESP_OK;}
inline int httpd_ws_send_frame_async(httpd_handle_t h,int fd,httpd_ws_frame_t*f){auto fn=nativeSend.at(fd);const char header[2]={char(0x82),char(f->len)};if(fn(h,fd,header,2,0)<0||fn(h,fd,(const char*)f->payload,f->len,0)<0)return ESP_FAIL;sentPayloads.emplace_back(f->payload,f->payload+f->len);return ESP_OK;}
inline int httpd_resp_set_type(httpd_req_t*r,const char*v){r->mime=v;return ESP_OK;}
inline int httpd_resp_set_hdr(httpd_req_t*r,const char*k,const char*v){r->responseHeaders[k]=v;return ESP_OK;}
inline int httpd_resp_send(httpd_req_t*r,const char*p,size_t n){r->response.assign(p,p+n);return ESP_OK;}
inline int httpd_resp_send_err(httpd_req_t*r,int status,const char*){r->status=status;return ESP_OK;}
