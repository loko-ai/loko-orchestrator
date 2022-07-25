from loko_orchestrator.model.components import Component
from loko_orchestrator.business.engine import Counter, Head, RSampler, Grouper  # , Subset
from loko_orchestrator.resources.doc_commons_component import head_doc, sampler_doc, grouper_doc, counter_doc


class CounterComponent(Component):
    def __init__(self):
        super().__init__("Counter", group="Common", description=counter_doc, icon="RiSettings6Fill", configured=True)

    def create(self, **kwargs):
        return Counter(**kwargs)


class HeadComponent(Component):
    def __init__(self):
        super().__init__("Head", group="Common", description=head_doc, icon="RiSpyFill",
                         args=[{"name": "n", "type": "number", "label": "Number of elements"}], values=dict(n=10),
                         configured=True)

    def create(self, n, **kwargs):
        return Head(int(n), **kwargs)


#
# class SubsetComponent(Component):
#     def __init__(self):
#         super().__init__("Subset", group="Common", icon="RiSpyFill",
#                          args=[{"name": "start", "type": "number", "label": "Starts From", "helper":"Starting position element"},
#                                {"name": "end", "type": "number", "label": "Ends To","helper":"Ending position element"}],
#                          values=dict(start=10, end=20),
#                          configured=True)
#     def create(self, n, **kwargs):
#         return Subset(int(n), **kwargs)


class SamplerComponent(Component):
    def __init__(self):
        super().__init__("Sampler", group="Common", description=sampler_doc,
                         args=[{"name": "k", "type": "number", "label": "Sample size"}],
                         values=dict(k=10), icon="RiBarChartGroupedFill", configured=True)

    def create(self, k, **kwargs):
        return RSampler(int(k), **kwargs)


class GrouperComponent(Component):
    def __init__(self):
        super().__init__("Grouper", group="Common", description=grouper_doc, icon="RiGroupFill",
                         args=[dict(name="n", label="Group size", type="number")], values=dict(n=10), configured=True)

    def create(self, n=10, **kwargs):
        return Grouper(int(n), **kwargs)
