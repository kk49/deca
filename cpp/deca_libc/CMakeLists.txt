cmake_minimum_required(VERSION 3.3)

project(decac)

add_library(
	decac
	SHARED
	src/process_image.c
)

