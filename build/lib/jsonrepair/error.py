class JSONRepairError(Exception):
    def __init__(self, message: str, position: int):
        super().__init__(f"{message} at position {position}")
        self.position = position
