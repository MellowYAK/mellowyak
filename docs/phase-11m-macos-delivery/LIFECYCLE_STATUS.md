# macOS lifecycle status

Packaged clean launch, second-instance exit, existing-instance activation request, exactly one engine,
supervised engine replacement after `SIGKILL`, explicit process exit and zero engine children after
quit are `VERIFIED_WORKING`.

Close-to-tray and tray menu logic are implemented and source tested; physical menu/close interaction,
real login relaunch, sleep/wake and lock/unlock are `IMPLEMENTED_NOT_RUNTIME_VERIFIED`.
