"""Version handler."""
from awesomeversion import AwesomeVersion


class Version(AwesomeVersion):
    @property
    def tags(self):
        tags = ["latest"]
        tags.append(str(self.section(0)))
        if self.sections > 1:
            tags.append(f"{self.section(0)}.{self.section(1)}")
        if self.sections > 2:
            tags.append(f"{self.section(0)}.{self.section(1)}.{self.section(2)}")
        return tags
