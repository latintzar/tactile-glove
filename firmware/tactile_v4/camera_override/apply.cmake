# Rebind only the two camera driver translation units after IDF project() has
# materialized the managed component. The managed component remains immutable.
set(_camera_component "espressif__esp32-camera")
idf_component_get_property(_camera_target ${_camera_component} COMPONENT_LIB)
idf_component_get_property(_camera_dir ${_camera_component} COMPONENT_DIR)
if(NOT TARGET ${_camera_target})
    message(FATAL_ERROR "camera override: target ${_camera_target} is unavailable")
endif()
if(NOT EXISTS "${_camera_dir}/driver/esp_camera.c" OR NOT EXISTS "${_camera_dir}/driver/cam_hal.c")
    message(FATAL_ERROR "camera override: unexpected esp32-camera component layout")
endif()
set(_camera_generated "${CMAKE_CURRENT_BINARY_DIR}/camera_override")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_LIST_DIR}/prepare_override.py"
    "${CMAKE_CURRENT_LIST_DIR}/driver/esp_camera.c"
    "${CMAKE_CURRENT_LIST_DIR}/driver/cam_hal.c"
    "${_camera_dir}/driver/esp_camera.c"
    "${_camera_dir}/driver/cam_hal.c"
)
find_package(Python3 COMPONENTS Interpreter REQUIRED)
execute_process(
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_LIST_DIR}/prepare_override.py"
            --source-root "${_camera_dir}/driver"
            --output "${_camera_generated}"
    RESULT_VARIABLE _camera_prepare_result
    OUTPUT_VARIABLE _camera_prepare_out
    ERROR_VARIABLE _camera_prepare_err
)
if(NOT _camera_prepare_result EQUAL 0)
    message(FATAL_ERROR "camera override configure failed: ${_camera_prepare_out}${_camera_prepare_err}")
endif()
get_target_property(_camera_sources ${_camera_target} SOURCES)
set(_camera_removed 0)
set(_camera_kept "")
foreach(_source IN LISTS _camera_sources)
    if(_source MATCHES "/driver/(esp_camera|cam_hal)\\.c$")
        math(EXPR _camera_removed "${_camera_removed}+1")
    else()
        list(APPEND _camera_kept "${_source}")
    endif()
endforeach()
if(NOT _camera_removed EQUAL 2)
    message(FATAL_ERROR "camera override: expected two driver sources, removed ${_camera_removed}")
endif()
set_property(TARGET ${_camera_target} PROPERTY SOURCES
    ${_camera_kept}
    "${_camera_generated}/esp_camera.c"
    "${_camera_generated}/cam_hal.c"
)
message(STATUS "camera override: ${_camera_target} uses hash-checked generated sources")
