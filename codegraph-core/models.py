"""Data models for codegraph entities.

These are plain dict-based models (rows returned by pymysql DictCursor).
The types here serve as documentation and type-annotation helpers.
"""

from typing import TypedDict


class ServiceEntry(TypedDict, total=False):
    id: int
    entry_type: str
    name: str
    uri: str
    interface: str
    bean_ref: str
    method_name: str
    context_name: str
    command_id: str
    business_type: str
    request_class: str
    response_class: str
    exe_mode: str
    chain_id: str
    flow_id: str
    is_rec_order: str
    is_check_concurrent: str
    enable_idempotent: str
    context_initializer: str
    listeners: str
    xml_path: str


class Flow(TypedDict, total=False):
    id: int
    flow_type: str
    flow_id: str
    real_flow_id: str
    template_name: str
    description: str
    ref_template: str
    entry_point: str
    version: str
    plan: str
    xml_path: str


class Logic(TypedDict, total=False):
    id: int
    chain_id: str
    context_id: str
    xml_path: str


class Bean(TypedDict, total=False):
    id: int
    bean_id: str
    bean_class: str
    declaration_type: str
    scope: str
    parent_bean: str
    factory_method: str
    init_method: str
    xml_path: str
    java_path: str


class State(TypedDict, total=False):
    id: int
    flow_id: str
    state_name: str
    state_order: int
    xml_path: str


class FlowTask(TypedDict, total=False):
    id: int
    flow_id: str
    task_type: str
    logic: str
    task_order: int
    xml_path: str


class Activity(TypedDict, total=False):
    id: int
    flow_id: str
    state_name: str
    activity_id: str
    activity_name: str
    logic: str
    logic_type: str
    activity_order: int
    is_inherited: int
    is_overridden: int
    original_logic: str
    xml_path: str


class Transition(TypedDict, total=False):
    id: int
    flow_id: str
    state_name: str
    activity_id: str
    method: str
    trans_type: str
    next_target: str
    criteria_operator: str
    criteria_value: str
    xml_path: str


class LogicStep(TypedDict, total=False):
    id: int
    chain_id: str
    logic_type: str
    step_order: int
    xml_path: str


class Bridge(TypedDict, total=False):
    id: int
    chain_id: str
    logic_type: str
    bridge_id: str
    is_skip: int
    is_suspend: int
    before_beans: str
    step_order: int
    bridge_order: int
    xml_path: str


class JavaClass(TypedDict, total=False):
    id: int
    class_name: str
    package_name: str
    full_qualified_name: str
    file_path: str
    extends_class: str
    implements_interfaces: str
    annotations: str
    is_interface: int
    is_abstract: int
    is_enum: int
    super_class_fqn: str
    imports: str
    semantic: str


class Interceptor(TypedDict, total=False):
    id: int
    context_name: str
    stack_name: str
    bean_ref: str
    interceptor_order: int
    xml_path: str


class JavaMethod(TypedDict, total=False):
    id: int
    class_fqn: str
    method_name: str
    return_type: str
    parameters: str
    full_signature: str
    modifiers: str
    annotations: str
    is_constructor: int
    file_path: str


class ModuleParameter(TypedDict, total=False):
    id: int
    module_id: str
    parameter_name: str
    param_key: str
    param_value: str
    xml_path: str