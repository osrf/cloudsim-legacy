cmake_minimum_required(VERSION 2.8)

project(CloudSim)
string(TOLOWER ${PROJECT_NAME} PROJECT_NAME_LOWER)
set(MAJOR_VERSION 1)
set(MINOR_VERSION 7)
set(PATCH_VERSION 3)

set(VERSION ${MAJOR_VERSION}.${MINOR_VERSION})
set(VERSION_FULL ${MAJOR_VERSION}.${MINOR_VERSION}.${PATCH_VERSION})

message(STATUS "${PROJECT_NAME} version ${VERSION_FULL}")

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/VERSION.in ${CMAKE_CURRENT_SOURCE_DIR}/VERSION)

########################################
# Package Creation: 
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Infrastructure for launching robotics simulations in the cloud")
set(CPACK_PACKAGE_VENDOR "Open Source Robotics Foundation, Inc.")
set(CPACK_PACKAGE_DESCRIPTION_FILE "${CMAKE_CURRENT_SOURCE_DIR}/README")
set(CPACK_RESOURCE_FILE_LICENSE "${CMAKE_CURRENT_SOURCE_DIR}/LICENSE")
set(CPACK_PACKAGE_VERSION_MAJOR ${MAJOR_VERSION})
set(CPACK_PACKAGE_VERSION_MINOR ${MINOR_VERSION})
set(CPACK_PACKAGE_VERSION_PATCH ${PATCH_VERSION})
set(CPACK_SOURCE_PACKAGE_FILE_NAME "${PROJECT_NAME_LOWER}-${VERSION_FULL}")
set(CPACK_PACKAGE_INSTALL_DIRECTORY "${PROJECT_NAME_LOWER}")
set(CPACK_SOURCE_GENERATOR "TBZ2")
list(APPEND CPACK_SOURCE_IGNORE_FILES ";Ogre.log;TODO;/.hg/;.swp$;/build/;.hgtags;.hgignore")
include(CPack)

########################################
# Testing
enable_testing()
set(TEST_SCRIPTS
  tools/rest_integration_test.py
)

foreach(script ${TEST_SCRIPTS})
  string(REGEX REPLACE "/" "_" test_name ${script})
  add_test(NAME ${test_name} 
           WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
           COMMAND python ${script})
  set_tests_properties(${test_name} PROPERTIES TIMEOUT 1800)
  # Check that the test produced a result and create a failure if it didn't.
  # Guards against crashed and timed out tests.
  # Diabled until we have predictable test result file names, #8
  #add_test(check_${BINARY_NAME} ${PROJECT_SOURCE_DIR}/tools/check_test_ran.py ${CMAKE_BINARY_DIR}/test_results/${BINARY_NAME}.xml)
endforeach()

