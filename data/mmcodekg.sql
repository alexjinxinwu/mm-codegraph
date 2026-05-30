create table if not exists activities
(
    id             bigint           not null
        primary key,
    flow_id        text             not null,
    state_name     text             not null,
    activity_id    text             not null,
    activity_name  text             not null,
    logic          text             not null,
    logic_type     text             not null,
    activity_order bigint           not null,
    is_inherited   bigint default 0 not null,
    is_overridden  bigint default 0 not null,
    original_logic text             null,
    xml_path       text             not null
);

create index idx_activities_flow_id
    on activities (flow_id(255));

create table if not exists beans
(
    id               bigint not null
        primary key,
    bean_id          text   not null,
    bean_class       text   not null,
    declaration_type text   not null,
    scope            text   not null,
    parent_bean      text   not null,
    factory_method   text   not null,
    init_method      text   not null,
    xml_path         text   not null,
    java_path        text   null
);

create index idx_beans_bean_class
    on beans (bean_class(255));

create index idx_beans_bean_id
    on beans (bean_id(255));

create table if not exists bridges
(
    id           bigint           not null
        primary key,
    chain_id     text             not null,
    logic_type   text             not null,
    bridge_id    text             not null,
    is_skip      bigint default 0 not null,
    is_suspend   bigint default 0 not null,
    before_beans text             not null,
    step_order   bigint           not null,
    bridge_order bigint           not null,
    xml_path     text             not null
);

create index idx_bridges_bridge_id
    on bridges (bridge_id(255));

create index idx_bridges_chain_id
    on bridges (chain_id(255));

create table if not exists flow_tasks
(
    id         bigint not null
        primary key,
    flow_id    text   not null,
    task_type  text   not null,
    logic      text   not null,
    task_order bigint not null,
    xml_path   text   not null
);

create index idx_flow_tasks_flow_id
    on flow_tasks (flow_id(255));

create table if not exists flows
(
    id            bigint not null
        primary key,
    flow_type     text   not null,
    flow_id       text   not null,
    real_flow_id  text   null,
    template_name text   null,
    description   text   not null,
    ref_template  text   null,
    entry_point   text   null,
    version       text   null,
    plan          text   not null,
    xml_path      text   not null
);

create index idx_flows_flow_id
    on flows (flow_id(255));

create index idx_flows_flow_type
    on flows (flow_type(255));

create index idx_flows_real_flow_id
    on flows (real_flow_id(255));

create table if not exists interceptors
(
    id                bigint not null
        primary key,
    context_name      text   not null,
    stack_name        text   not null,
    bean_ref          text   not null,
    interceptor_order bigint not null,
    xml_path          text   not null
);

create table if not exists java_classes
(
    id                    bigint           not null
        primary key,
    class_name            text             not null,
    package_name          text             not null,
    full_qualified_name   text             not null,
    file_path             text             not null,
    extends_class         text             not null,
    implements_interfaces text             not null,
    annotations           text             not null,
    is_interface          bigint default 0 not null,
    is_abstract           bigint default 0 not null,
    is_enum               bigint default 0 not null,
    super_class_fqn       text             not null,
    imports               text             not null,
    semantic              text             not null
);

create index idx_java_classes_class_name
    on java_classes (class_name(255));

create index idx_java_classes_extends_class
    on java_classes (extends_class(255));

create index idx_java_classes_fqn
    on java_classes (full_qualified_name(255));

create index idx_java_classes_implements_interfaces
    on java_classes (implements_interfaces(255));

create index idx_java_classes_package_name
    on java_classes (package_name(255));

create table if not exists java_methods
(
    id             bigint           not null
        primary key,
    class_fqn      text             not null,
    method_name    text             not null,
    return_type    text             not null,
    parameters     text             not null,
    full_signature text             not null,
    modifiers      text             not null,
    annotations    text             not null,
    is_constructor bigint default 0 not null,
    file_path      text             not null
);

create index idx_java_methods_class_fqn
    on java_methods (class_fqn(255));

create index idx_java_methods_method_name
    on java_methods (method_name(255));

create table if not exists logic_steps
(
    id         bigint not null
        primary key,
    chain_id   text   not null,
    logic_type text   not null,
    step_order bigint not null,
    xml_path   text   not null
);

create index idx_logic_steps_chain_id
    on logic_steps (chain_id(255));

create table if not exists logics
(
    id         bigint not null
        primary key,
    chain_id   text   not null,
    context_id text   not null,
    xml_path   text   not null
);

create index idx_logics_chain_id
    on logics (chain_id(255));

create table if not exists module_parameters
(
    id             bigint not null
        primary key,
    module_id      text   not null,
    parameter_name text   not null,
    param_key      text   not null,
    param_value    text   not null,
    xml_path       text   not null
);

create index idx_module_params_module_id
    on module_parameters (module_id(255));

create table if not exists service_entries
(
    id                  bigint not null
        primary key,
    entry_type          text   not null,
    name                text   not null,
    uri                 text   null,
    interface           text   null,
    bean_ref            text   null,
    method_name         text   null,
    context_name        text   null,
    command_id          text   null,
    business_type       text   null,
    request_class       text   null,
    response_class      text   null,
    exe_mode            text   null,
    chain_id            text   null,
    flow_id             text   null,
    is_rec_order        text   null,
    is_check_concurrent text   null,
    enable_idempotent   text   null,
    context_initializer text   null,
    listeners           text   null,
    xml_path            text   not null
);

create index idx_service_entries_chain_id
    on service_entries (chain_id(255));

create index idx_service_entries_flow_id
    on service_entries (flow_id(255));

create index idx_service_entries_name
    on service_entries (name(255));

create table if not exists states
(
    id          bigint not null
        primary key,
    flow_id     text   not null,
    state_name  text   not null,
    state_order bigint not null,
    xml_path    text   not null
);

create index idx_states_flow_id
    on states (flow_id(255));

create table if not exists transitions
(
    id                bigint not null
        primary key,
    flow_id           text   not null,
    state_name        text   not null,
    activity_id       text   not null,
    method            text   not null,
    trans_type        text   not null,
    next_target       text   not null,
    criteria_operator text   not null,
    criteria_value    text   not null,
    xml_path          text   not null
);

create index idx_transitions_flow_id
    on transitions (flow_id(255));

