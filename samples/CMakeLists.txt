cmake_minimum_required(VERSION 3.16)

project(lldb_mix_samples C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

function(lldb_mix_sample name)
  add_executable(${name} ${ARGN})
  target_compile_features(${name} PRIVATE c_std_11)
  if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(${name} PRIVATE -g -O0)
  endif()
endfunction()

lldb_mix_sample(sample_basic sample_basic.c)
lldb_mix_sample(sample_branch sample_branch.c)
