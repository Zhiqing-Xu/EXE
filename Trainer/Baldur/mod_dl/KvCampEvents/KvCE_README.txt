Camp Event Notifications
by Kvalyr


Script Extender is Required for this mod



Description:
BG3 is full of events at the camp that players miss due to not resting often enough, or not resting during certain windows of opportunity that the game expects.

This mod regularly checks for pending/available 'Camp Night Events' and adds a floating exclamation point above your main character's head (similar to the one that shows on companions when they have something to say to you).
When this symbol shows up, you should go to camp and talk to your companions and/or long rest, to avoid missing out on these events.

A future version of this mod will adjust the game logic to allow multiple events to play out in a single night too.


Installation:
* Install BG3 Mod Manager (Vortex might work, but I don't use it and have no interest in troubleshooting it. If you use it, you're on your own.)
* Install BG3 Script Extender (You can install this easily using BG3 Mod Manager)
* Optional: Create an empty folder called 'Osiris Data' if it doesn't already exist at this location:
C:\Users/[USERNAME]\AppData\Local\Larian Studios\Baldur's Gate 3\Osiris Data\


Uninstallation:
* See this article: https://www.nexusmods.com/baldursgate3/articles/168
* It's almost never a good idea to remove mods from an ongoing playthrough.
* This one should be safe to remove in most cases as of v0.4, but there are no promises.


Configuration:
* Configuration is optional - Most players can just install and play
* See this article for instructions on configuring the mod: https://www.nexusmods.com/baldursgate3/articles/170
* i.e.; Enabling/Disabling the exclamation mark, statuses, etc.


FAQ:

Q: What are "Camp Night Events"?
A: Cutscenes, dream sequences, dialogues, etc. that happen when you go to bed for a long rest.

Q: What does this mod actually do?
A: At various times (when you end a dialog, change regions, etc.) It simulates the checks the game normally does when you click on your bedroll to switch to "Night Mode", and tells you if there are Camp Night Events waiting to happen.

Q: I just rested and the mod is STILL telling me that I have camp events waiting. Why?
A: Yep. Go rest again. BG3 is weird like that.
When you Long Rest, the game looks at what events are waiting and eligible to be played, then chooses the one event with the highest priority. Only the one highest priority event is then played for a single night of rest. Other events are put back into 'the queue' until your next rest.
A later version of this mod will have a feature to allow multiple events to happen in one rest.

Q: Will it mess with my quests/relationships/story/cutscenes?
A: No. This mod only 'queries' the game state to find out when events are pending/eligible/queued and tells you about it. It doesn't otherwise manipulate or change these events in any way.

Q: I got the notification that there were events waiting, but nothing happened when I long-rested - What gives?
A: This mod errs on the side of telling you when there are probably events waiting to happen, rather than risking you missing some. Try talking to everyone in camp and/or resting again.
* Sometimes the function that determines this will get it wrong because it's imitating the game's logic imperfectly. I'll improve this over time and in later versions.
* Also, sometimes the game is just weird about how and when it 'dismisses' events from being eligible to play.
* Also, sometimes characters wanting to talk to you at the camp makes the mod think there are camp events waiting. A future version will track that separately.

Q: The mod tells me there are events waiting, but I don't need to rest and don't want to waste my resources. What do I do?
A: Do a 'partial rest' without using camp supplies. You'll still trigger camp events.


Planned Features:

* Separate logic for pending 'Relationship Dialogue' events. i.e.; Companions wanting to talk to you.
* New logic to allow multiple events to play out during a single rest/night.

Credits:
* Norbyte for LSLib & Script Extender
* LaughingLeader for BG3 Mod Manager
* ShinyHobo for the BG3 MultiTool
* Larian Studios for the best CRPG in years
