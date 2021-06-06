.PHONY: install_hourly install_daily
HOURLY=org.dltj.kmtools.hourly
DAILY=org.dltj.kmtools.daily

all: install_hourly install_daily

install_hourly:
	cp $(HOURLY).plist ~/Library/LaunchAgents
	launchctl unload ~/Library/LaunchAgents/$(HOURLY).plist
	launchctl load ~/Library/LaunchAgents/$(HOURLY).plist
	launchctl start $(HOURLY)

install_daily:
	cp $(DAILY).plist ~/Library/LaunchAgents
	launchctl unload ~/Library/LaunchAgents/$(DAILY).plist
	launchctl load ~/Library/LaunchAgents/$(DAILY).plist
	launchctl start $(DAILY)

