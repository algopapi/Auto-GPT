from auto_gpt.config import Config
from auto_gpt.utils.initialization_utils import get_organization


class AutoGPT:
    def __init__(
        self,
    ):  
        self.initial_budget = 10000
        self.global_cfg = Config()
        self.organization = get_organization()

    def run(self):
        while True:
            self.organization.run()


def main():
    auto_gpt = AutoGPT()
    auto_gpt.run()


if __name__ == "__main__":
    main()
