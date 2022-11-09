cmake_minimum_required(VERSION 3.3)

project(bin2xml VERSION 1.0.0)

add_executable(
	bin2xml
	src/bin2xml.cpp
)

target_link_libraries(bin2xml havok)
