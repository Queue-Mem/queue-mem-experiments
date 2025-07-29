def stop_traffic():
    pktgen.app_disable(0)


print("Stopping pktgen")
stop_traffic()
