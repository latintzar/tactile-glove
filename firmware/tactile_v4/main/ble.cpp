#include "app.hpp"
#include "freertos/task.h"
#include "esp_err.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/ble_store.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"
#include <atomic>
#include <algorithm>
#include <cstdio>
#include <cstring>
extern "C" void ble_store_config_init(void);
extern std::atomic<uint32_t> bleDrops;
static std::atomic<uint16_t> connection{BLE_HS_CONN_HANDLE_NONE};static std::atomic<uint32_t> epoch{0};static uint16_t txHandle;static uint8_t ownAddress;
static ble_uuid128_t service=BLE_UUID128_INIT(0xE0,0x0D,0x18,0x2A,0x1C,0xE8,0x67,0x9B,0x5D,0x4D,0x8B,0xA8,0x01,0x00,0xC4,0xA4);
static ble_uuid128_t tx=BLE_UUID128_INIT(0xE0,0x0D,0x18,0x2A,0x1C,0xE8,0x67,0x9B,0x5D,0x4D,0x8B,0xA8,0x02,0x00,0xC4,0xA4);
static ble_uuid128_t rx=BLE_UUID128_INIT(0xE0,0x0D,0x18,0x2A,0x1C,0xE8,0x67,0x9B,0x5D,0x4D,0x8B,0xA8,0x03,0x00,0xC4,0xA4);
static ble_uuid128_t setup=BLE_UUID128_INIT(0xE0,0x0D,0x18,0x2A,0x1C,0xE8,0x67,0x9B,0x5D,0x4D,0x8B,0xA8,0x04,0x00,0xC4,0xA4);
static int access(uint16_t conn,uint16_t,ble_gatt_access_ctxt*c,void*){
 ble_gap_conn_desc d{};if(ble_gap_conn_find(conn,&d)||!d.sec_state.encrypted)return BLE_ATT_ERR_INSUFFICIENT_AUTHEN;
 if(c->op==BLE_GATT_ACCESS_OP_READ_CHR){if(!wifiSsid[0]||!wifiPassword[0])return BLE_ATT_ERR_UNLIKELY;char credentials[112];int n=snprintf(credentials,sizeof(credentials),"%s\n%s\n192.168.4.1\n7001\n7002",wifiSsid,wifiPassword);return os_mbuf_append(c->om,credentials,n)?BLE_ATT_ERR_INSUFFICIENT_RES:0;}
 if(c->op==BLE_GATT_ACCESS_OP_WRITE_CHR){uint16_t n=OS_MBUF_PKTLEN(c->om);if(n>31)return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;uint8_t p[32]{};p[0]=n;if(os_mbuf_copydata(c->om,0,n,p+1))return BLE_ATT_ERR_UNLIKELY;return xQueueSend(commands,p,0)==pdTRUE?0:BLE_ATT_ERR_INSUFFICIENT_RES;}return BLE_ATT_ERR_READ_NOT_PERMITTED;
}
static ble_gatt_chr_def characteristics[4];static ble_gatt_svc_def services[2];
static void advertise();
static int event(ble_gap_event*e,void*){
 switch(e->type){
 case BLE_GAP_EVENT_CONNECT:if(e->connect.status){advertise();break;}{ble_gap_conn_desc d{};ble_gap_conn_find(e->connect.conn_handle,&d);ble_store_key_sec key{};key.peer_addr=d.peer_id_addr;ble_store_value_sec value{};bool bonded=ble_store_read_peer_sec(&key,&value)==0;if(!bonded&&!pairingAllowed()){ble_gap_terminate(e->connect.conn_handle,BLE_ERR_REM_USER_CONN_TERM);break;}connection=e->connect.conn_handle;epoch++;ble_gap_security_initiate(e->connect.conn_handle);ble_gattc_exchange_mtu(e->connect.conn_handle,nullptr,nullptr);ble_gap_upd_params params{};params.itvl_min=6;params.itvl_max=12;params.supervision_timeout=400;ble_gap_update_params(e->connect.conn_handle,&params);}break;
 case BLE_GAP_EVENT_DISCONNECT:connection=BLE_HS_CONN_HANDLE_NONE;epoch++;xQueueReset(bleFrames);advertise();break;
 case BLE_GAP_EVENT_REPEAT_PAIRING:return BLE_GAP_REPEAT_PAIRING_IGNORE;
 case BLE_GAP_EVENT_ENC_CHANGE:if(e->enc_change.status)ble_gap_terminate(e->enc_change.conn_handle,BLE_ERR_REM_USER_CONN_TERM);break;
 default:break;}return 0;
}
static void advertise(){ble_hs_adv_fields f{};f.flags=BLE_HS_ADV_F_DISC_GEN|BLE_HS_ADV_F_BREDR_UNSUP;f.uuids128=&service;f.num_uuids128=1;f.uuids128_is_complete=1;ble_gap_adv_set_fields(&f);ble_hs_adv_fields scan{};const char*n=ble_svc_gap_device_name();scan.name=(uint8_t*)n;scan.name_len=strlen(n);scan.name_is_complete=1;ble_gap_adv_rsp_set_fields(&scan);ble_gap_adv_params p{};p.conn_mode=BLE_GAP_CONN_MODE_UND;p.disc_mode=BLE_GAP_DISC_MODE_GEN;ble_gap_adv_start(ownAddress,nullptr,BLE_HS_FOREVER,&p,event,nullptr);}
static void onSync(){ble_hs_id_infer_auto(0,&ownAddress);advertise();}
static void host(void*){nimble_port_run();nimble_port_freertos_deinit();}
static void notify(void*){Packet p{};uint32_t observed=epoch.load();bool delimiter=false;for(;;){if(xQueueReceive(bleFrames,&p,pdMS_TO_TICKS(100))!=pdTRUE)continue;uint32_t generation=epoch.load();uint16_t c=connection.load();ble_gap_conn_desc d{};if(c==BLE_HS_CONN_HANDLE_NONE||ble_gap_conn_find(c,&d)||!d.sec_state.encrypted)continue;if(generation!=observed){observed=generation;delimiter=true;}
 uint16_t at=0;while(at<p.size && epoch.load()==generation){uint16_t mtu=ble_att_mtu(c);if(mtu<23)break;uint16_t n=std::min<uint16_t>(p.size-at,mtu-3);uint8_t zero=0;os_mbuf*m=ble_hs_mbuf_from_flat(delimiter?&zero:p.data+at,delimiter?1:n);if(!m){bleDrops++;delimiter=delimiter||at!=0;break;}int rc=ble_gatts_notify_custom(c,txHandle,m);if(rc){bleDrops++;delimiter=delimiter||at!=0;break;}if(delimiter)delimiter=false;else at+=n;vTaskDelay(1);}
 }}
void beginBle(){ESP_ERROR_CHECK(nimble_port_init());ble_svc_gap_init();ble_svc_gatt_init();ble_svc_gap_device_name_set("Artisan Tactile V4");ble_hs_cfg.sync_cb=onSync;ble_hs_cfg.sm_bonding=1;ble_hs_cfg.sm_sc=1;ble_hs_cfg.sm_io_cap=BLE_HS_IO_NO_INPUT_OUTPUT;ble_hs_cfg.sm_our_key_dist=BLE_SM_PAIR_KEY_DIST_ENC|BLE_SM_PAIR_KEY_DIST_ID;ble_hs_cfg.sm_their_key_dist=BLE_SM_PAIR_KEY_DIST_ENC|BLE_SM_PAIR_KEY_DIST_ID;
 characteristics[0].uuid=&tx.u;characteristics[0].flags=BLE_GATT_CHR_F_NOTIFY;characteristics[0].val_handle=&txHandle;
 characteristics[1].uuid=&rx.u;characteristics[1].flags=BLE_GATT_CHR_F_WRITE|BLE_GATT_CHR_F_WRITE_ENC;characteristics[1].access_cb=access;
 characteristics[2].uuid=&setup.u;characteristics[2].flags=BLE_GATT_CHR_F_READ|BLE_GATT_CHR_F_READ_ENC;characteristics[2].access_cb=access;
 services[0].type=BLE_GATT_SVC_TYPE_PRIMARY;services[0].uuid=&service.u;services[0].characteristics=characteristics;assert(!ble_gatts_count_cfg(services));assert(!ble_gatts_add_svcs(services));ble_store_config_init();nimble_port_freertos_init(host);createCheckedTask(notify,"ble-frames",4096,nullptr,5,nullptr,0);
}
