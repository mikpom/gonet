class DataNotProvidedError(Exception):
    pass

class InputValidationError(Exception):
    pass

class TooManySeparatorsError(InputValidationError):
    pass

class TooManyEntriesError(InputValidationError):
    pass

class TooManyEntriesGraphError(InputValidationError):
    pass

class GenesNotIdentifiedError(InputValidationError):
    pass
    # genelist = []

    # def __init__(self, genelist, *args, **kwargs):
    #     self.genelist = genelist
    #     Exception(self, *args, **kwargs)

class BgGenesNotIdentifiedError(InputValidationError):
    pass

class InvalidGOTermError(InputValidationError):
    pass
