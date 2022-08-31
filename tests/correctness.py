from .utils import GossipEnabledTests


class ConformanceTests(GossipEnabledTests):
    def test_api_conformance(self):
        # TODO: Create an API subprocess that runs and will be called by the mockup client
        pass


class CorrectnessTests(GossipEnabledTests):
    def test_correct_estimate(self):
        # TODO: Create a bunch of subprocesses, each with other ports and keys and let them do their job,
        #  then query them for their size estimates (attention: test probably takes incredibly long!)
        pass
