class InputValidationError(Exception):
    pass

class GenesNotIdentifiedError(Exception):
    genelist = []

    def __init__(self, genelist, *args, **kwargs):
        self.genelist = genelist
        Exception(self, *args, **kwargs)

class DataNotProvidedError(Exception):
    pass

class TestNotApplicableError(Exception):
    pass

class RunFailError(Exception):
    pass
