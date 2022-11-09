cmake_minimum_required(VERSION 3.3)

project(deca_cpp)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_subdirectory(extern/HavokLib)
add_subdirectory(cpp)
