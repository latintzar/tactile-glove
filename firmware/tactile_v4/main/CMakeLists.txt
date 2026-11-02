idf_component_register(SRCS "app.cpp" "ble.cpp" "usb.cpp" "storage.cpp" "http.cpp" "web/web_assets.cpp" INCLUDE_DIRS "." REQUIRES esp_driver_gpio esp_driver_gptimer esp_driver_spi esp_driver_i2c esp_driver_sdspi esp_adc esp_timer esp_wifi esp_event esp_netif nvs_flash esp_psram bt fatfs sdmmc esp_hw_support esp_http_server)
target_compile_features(${COMPONENT_LIB} PUBLIC cxx_std_17)
# Keep literals for templated IRAM capture functions beside their code.
target_compile_options(${COMPONENT_LIB} PRIVATE -mtext-section-literals)
