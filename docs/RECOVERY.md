# Recovery

No automatic job resume is allowed after:

- E-stop
- Pi reboot
- Power failure
- Controller reset
- Unexpected laser USB loss

After recovery, LightBurn reconnects and homes the machine. Current LightBurn setup is expected to home on connection.

K1 is the hard E-stop path and kills the laser controller completely. If K1 is intentionally dropped, laser USB disappearance is expected and should not create a second critical USB fault.

Software E-stop clear requires the housing E-stop switch to cycle active and back to OK: PC15 low, then PC15 high. Returning PC15 high without a prior low transition does not clear a software E-stop.
