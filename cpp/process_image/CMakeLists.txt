cmake_minimum_required(VERSION 3.3)

project(process_image)

# gcc -fPIC -shared -O3 deca/process_image.c -o process_image.so

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
