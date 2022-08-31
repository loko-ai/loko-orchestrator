class Field:
    def __init__(self, name, type, description="", label=None, validation=None, fragment=None, options=None,
                 advanced=False, value=None):
        self.name = name
        self.type = type
        self.description = description
        self.label = label
        self.validation = validation
        self.fragment = fragment
        self.advanced = advanced
        self.options = options
        self.value = value


class Options(Field):
    def __init__(self, name, options, value=None, description=None, label=None, advanced=False, validation=None):
        super().__init__(name=name, type="select", description=description, label=label, advanced=advanced,
                         validation=validation, value=value)
        self.options = options


class Text(Field):
    def __init__(self, name, description=None, label=None, advanced=False, validation=None, value=None):
        super().__init__(name=name, type="text", description=description, label=label, advanced=advanced,
                         validation=validation)


class Component:
    def __init__(self, name, events=None, description=None, group=None, inputs=None, outputs=None, args=None,
                 click=None, icon=None, values=None,
                 configured=False, **kwargs):
        self.name = name
        self.events = events
        self.description = description
        self.inputs = inputs if inputs is not None else ["input"]
        self.inputs = [x if isinstance(x, dict) else dict(id=x, label=x) for x in self.inputs]
        self.outputs = outputs if outputs is not None else ["output"]
        self.outputs = [x if isinstance(x, dict) else dict(id=x, label=x) for x in self.outputs]
        self.configured = configured
        self.options = {"group": group, "args": args or [], "click": click, "icon": icon, "values": values or {}}

    def create(self):
        pass


required = {"required": "Required field"}
