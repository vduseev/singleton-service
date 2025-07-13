# BaseService

::: singleton_service.BaseService
    options:
      members:
        - __new__
        - initialize
        - ping
        - _initialize_impl
        - _get_initialization_order
        - _get_all_dependencies
        - _raise_on_circular_dependencies
      show_root_heading: true
      show_source: false
      heading_level: 2
      docstring_style: google
      docstring_options:
        ignore_init_summary: true
      filters:
        - "!^_.*"  # Hide private methods except the ones we explicitly include
        - "^_initialize_impl"
        - "^_get_initialization_order" 
        - "^_get_all_dependencies"
        - "^_raise_on_circular_dependencies"