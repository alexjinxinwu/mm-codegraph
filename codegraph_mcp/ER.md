# ER

 ```mermaid
erDiagram
    service_entries {
        bigint id PK
        string entry_type
        string name
        string uri
        string interface
        string bean_ref
        string method_name
        string context_name
        string command_id
        string business_type
        string request_class
        string response_class
        string exe_mode
        string chain_id
        string flow_id
        string is_rec_order
        string is_check_concurrent
        string enable_idempotent
        string context_initializer
        string listeners
        string xml_path
    }

    flows {
        bigint id PK
        string flow_type
        string flow_id
        string real_flow_id
        string template_name
        string description
        string ref_template
        string entry_point
        string version
        string plan
        string xml_path
    }

    logics {
        bigint id PK
        string chain_id
        string context_id
        string xml_path
    }

    beans {
        bigint id PK
        string bean_id
        string bean_class
        string declaration_type
        string scope
        string parent_bean
        string factory_method
        string init_method
        string xml_path
        string java_path
    }

    states {
        bigint id PK
        string flow_id
        string state_name
        bigint state_order
        string xml_path
    }

    flow_tasks {
        bigint id PK
        string flow_id
        string task_type
        string logic
        bigint task_order
        string xml_path
    }

    activities {
        bigint id PK
        string flow_id
        string state_name
        string activity_id
        string activity_name
        string logic
        string logic_type
        bigint activity_order
        bigint is_inherited
        bigint is_overridden
        string original_logic
        string xml_path
    }

    transitions {
        bigint id PK
        string flow_id
        string state_name
        string activity_id
        string method
        string trans_type
        string next_target
        string criteria_operator
        string criteria_value
        string xml_path
    }

    logic_steps {
        bigint id PK
        string chain_id
        string logic_type
        bigint step_order
        string xml_path
    }

    bridges {
        bigint id PK
        string chain_id
        string logic_type
        string bridge_id
        bigint is_skip
        bigint is_suspend
        string before_beans
        bigint step_order
        bigint bridge_order
        string xml_path
    }

    java_classes {
        bigint id PK
        string class_name
        string package_name
        string full_qualified_name
        string file_path
        string extends_class
        string implements_interfaces
        string annotations
        bigint is_interface
        bigint is_abstract
        bigint is_enum
        string super_class_fqn
        string imports
        string semantic
    }

    interceptors {
        bigint id PK
        string context_name
        string stack_name
        string bean_ref
        bigint interceptor_order
        string xml_path
    }

    java_methods {
        bigint id PK
        string class_fqn
        string method_name
        string return_type
        string parameters
        string full_signature
        string modifiers
        string annotations
        bigint is_constructor
        string file_path
    }

    module_parameters {
        bigint id PK
        string module_id
        string parameter_name
        string param_key
        string param_value
        string xml_path
    }

    service_entries ||--o{ flows : "flow_id -> flow_id"
    service_entries ||--o{ logics : "chain_id -> chain_id"
    service_entries ||--o{ beans : "bean_ref -> bean_id"

    flows ||--o{ states : "flow_id -> flow_id"
    flows ||--o{ flow_tasks : "flow_id -> flow_id"
    flows ||--o{ activities : "flow_id -> flow_id"
    flows ||--o{ transitions : "flow_id -> flow_id"

    states ||--o{ activities : "flow_id+state_name -> flow_id+state_name"
    states ||--o{ transitions : "flow_id+state_name -> flow_id+state_name"
    activities ||--o{ transitions : "activity_id -> activity_id"

    logics ||--o{ activities : "chain_id <- logic (逻辑关联)"
    logics ||--o{ flow_tasks : "chain_id <- logic (逻辑关联)"

    logics ||--o{ logic_steps : "chain_id -> chain_id"
    logics ||--o{ bridges : "chain_id -> chain_id"
    logic_steps ||--o{ bridges : "chain_id -> chain_id"

    bridges ||--|| java_classes : "before_beans -> full_qualified_name"
    beans ||--|| java_classes : "bean_class -> full_qualified_name"
    beans ||--o{ interceptors : "bean_id -> bean_ref"
    java_classes ||--o{ java_methods : "full_qualified_name -> class_fqn"
 ```
