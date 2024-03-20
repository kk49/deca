cmake_minimum_required(VERSION 3.3)

project(process_image)

# gcc -fPIC -shared -O3 deca/process_image.c -o process_image.so

# Some versions of CMake don't define _USRDLL and _WINDLL macros for a shared libraries.
# It will cause lack of __declspec(dllexport) declaration and produce an empty DLLs on Windows.
# We should add _USRDLL and _WINDLL flags here for MSVC.
if(CMAKE_CXX_COMPILER_ID MATCHES "MSVC")
  set(CMAKE_C_FLAGS_DEBUG "/D_USRDLL /D_WINDLL /MT")
  set(CMAKE_C_FLAGS_RELEASE "/D_USRDLL /D_WINDLL /MT")
  set(CMAKE_CXX_FLAGS_DEBUG "/D_USRDLL /D_WINDLL /MT")
  set(CMAKE_CXX_FLAGS_RELEASE "/D_USRDLL /D_WINDLL /MT")
endif()

add_library(
	process_image
	SHARED
	src/process_image.c
)

set_target_properties(
	process_image
	PROPERTIES
	PREFIX ""
)
