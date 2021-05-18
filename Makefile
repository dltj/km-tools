.PHONY: install
HOURLY=org.dltj.kmtools.hourly

all: install

install:
	cp $(HOURLY).plist ~/Library/LaunchAgents
	launchctl unload ~/Library/LaunchAgents/org.dltj.kmtools.hourly.plist
	launchctl load ~/Library/LaunchAgents/$(HOURLY).plist
	launchctl start $(HOURLY)

