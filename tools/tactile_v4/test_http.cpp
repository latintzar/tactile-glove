#define V4_HTTP_NATIVE
#include "../../firmware/tactile_v4/main/http.cpp"
#include <iostream>
#include <fstream>
const uint8_t gzipFixture[]={31,139,8,0};
const WebAsset webAssets[]={{"/","text/html",gzipFixture,sizeof(gzipFixture)},{"/app.js","text/javascript",gzipFixture,sizeof(gzipFixture)}};
const size_t webAssetCount=2;
VideoFrame*video(uint32_t seq){auto*f=new VideoFrame;f->bytes=38;f->storage=new uint8_t[39]{};f->storage[0]=1;f->data=f->storage+1;uint8_t jpeg[]={255,216,1,2,255,217};V4::jpegHeader(f->data,seq,1000,6,V4::crc32(jpeg,6),640,480);memcpy(f->data+32,jpeg,6);return f;}
int main(int argc,char**argv){unsigned checks=0;beginBrowser();assert(nativeRoutes.size()==2&&nativeConfig.server_port==80&&browserFrames->cap==64);checks++;
 httpd_req_t r;r.headers={{"Origin","http://192.168.4.1"},{"Host","192.168.4.1"}};assert(websocket(&r)==ESP_OK&&browserFd==5);httpd_req_t duplicate=r;duplicate.fd=6;assert(websocket(&duplicate)==ESP_FAIL&&browserFd==5);checks++;
 httpd_req_t hostile=r;hostile.fd=7;hostile.headers["Origin"]="http://untrusted.example";assert(websocket(&hostile)==ESP_FAIL);checks++;
 uint8_t payload[128]{};queueBrowserPacket(V4::KIND_SCAN,1,payload,94);assert(browserFrames->items.empty()&&browserSequence==0);queueBrowserPacket(V4::KIND_FEATURE,2,payload,128);assert(browserFrames->items.size()==1&&browserSequence==1);sendWork(nullptr);assert(sentPayloads.size()==1&&sentPayloads[0][0]==0&&sentPayloads[0].back()==0);checks++;
 for(unsigned i=0;i<70;i++){queueBrowserPacket(V4::KIND_FEATURE,3+i,payload,128);}assert(browserFrames->items.size()==64&&browserDrops==6&&browserSequence==71);uint8_t visible[8];browserStatus(visible);assert(V4::get32(visible)==6&&V4::get32(visible+4)==0);sendWork(nullptr);assert(browserFrames->items.size()==56);checks++;
 auto*a=video(10);publishBrowserVideo(a);assert(a->refs==2);releaseVideo(a);auto*b=video(11);publishBrowserVideo(b);assert(freedVideos==1&&b->refs==2);browserStatus(visible);assert(V4::get32(visible+4)==1);releaseVideo(b);sendWork(nullptr);assert(sentPayloads.back().size()==39&&sentPayloads.back()[0]==1&&!memcmp(sentPayloads.back().data()+1,"GV4J",4));size_t n=sentPayloads.size();xQueueReset(browserFrames);sendWork(nullptr);assert(sentPayloads.size()==n);checks++;
 r.method=0;r.incoming={'R','A','W',' ','2','0'};assert(websocket(&r)==ESP_OK);uint8_t command[32];assert(xQueueReceive(commands,command,0)&&command[0]==6&&!memcmp(command+1,"RAW 20",6));r.incoming.assign(32,'A');assert(websocket(&r)==ESP_FAIL);r.incoming={'L','A','B','E','L',' ','b','a','d'};assert(websocket(&r)==ESP_FAIL);r.incoming={'F','E','A','T','U','R','E','S'};r.incomingFinal=false;assert(websocket(&r)==ESP_FAIL);r.incomingFinal=true;r.incomingType=HTTPD_WS_TYPE_BINARY;assert(websocket(&r)==ESP_FAIL);checks++;
 r.incomingType=HTTPD_WS_TYPE_TEXT;for(unsigned i=0;i<8;i++)assert(websocket(&r)==ESP_OK);assert(websocket(&r)==ESP_FAIL);xQueueReset(commands);checks++;
 httpd_req_t staticReq;staticReq.uri="/app.js?version=2";assert(asset(&staticReq)==ESP_OK&&staticReq.response.size()==4&&staticReq.responseHeaders["Content-Encoding"]=="gzip"&&staticReq.mime=="text/javascript");staticReq.uri="/../secret";assert(asset(&staticReq)==ESP_OK&&staticReq.status==404);checks++;
 queueBrowserPacket(V4::KIND_FEATURE,9,payload,128);socketBlocked=true;uint64_t before=nativeTime;sendWork(nullptr);assert(browserFd==-1&&nativeTime-before>=200000&&nativeTime-before<202000&&browserFrames->items.empty()&&latestVideo==nullptr&&freedVideos==2);socketBlocked=false;checks++;
 r.method=HTTP_GET;r.fd=8;assert(websocket(&r)==ESP_OK);auto*c=video(11);publishBrowserVideo(c);releaseVideo(c);sendWork(nullptr);assert(sentPayloads.back()[0]==1&&latestClaimed);nativeConfig.close_fn(server,8);assert(browserFd==-1&&freedVideos==3);checks++;
 queueBrowserPacket(V4::KIND_FEATURE,10,payload,128);auto*d=video(12);publishBrowserVideo(d);assert(d->refs==1);releaseVideo(d);assert(browserFrames->items.empty());checks++;
 browserStatus(visible);uint8_t framed[256];auto encoded=V4::encodePacket(V4::KIND_BROWSER_STATUS,1,10,visible,8,framed);assert(encoded>8);if(argc>1){std::ofstream stream(argv[1],std::ios::binary);stream.write((char*)framed,encoded);}assert(V4::get32(visible)>=7&&V4::get32(visible+4)==1);checks++;
 delete browserFrames;delete videoMutex;delete commands;
 std::cout<<"{\"actual_http_cases\":"<<checks<<",\"status\":\"pass\"}\n";
}
