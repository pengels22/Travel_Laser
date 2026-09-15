# Recovery

No automatic job resume is allowed after:

- E-stop
- Pi reboot
- Power failure
- Controller reset
- Unexpected laser USB loss

After recovery, LightBurn reconnects and homes the machine. Current LightBurn setup is expected to home on connection.

K2 is the hard E-stop path and kills the laser controller completely. If K2 is intentionally dropped, laser USB disappearance is expected and should not create a second critical USB fault.
