#!/bin/sh
# Hand the container's wan/lan NICs to the VM: each NIC is bridged with a tap,
# the container drops the IP Docker gave it, and pfSense takes that same IP.
# Other NICs (the console network) stay with the container for the VNC web console.
set -eu
WAN_PREFIX=${WAN_PREFIX:-203.0.113.}
LAN_PREFIX=${LAN_PREFIX:-10.250.0.}

nic_for() {  # first interface holding an IPv4 address that starts with $1
  ip -o -4 addr show | awk -v p="$1" 'index($4, p) == 1 {print $2; exit}'
}

bridge() {  # bridge $1 (container NIC) with tap $2
  ip tuntap add "$2" mode tap
  ip link add "br-$2" type bridge
  ip addr flush dev "$1"
  ip link set "$1" master "br-$2"
  ip link set "$2" master "br-$2"
  ip link set "br-$2" up
  ip link set "$2" up
}

WAN=$(nic_for "$WAN_PREFIX"); LAN=$(nic_for "$LAN_PREFIX")
[ -n "$WAN" ] && [ -n "$LAN" ] || { echo "wan/lan NIC not found (WAN=$WAN LAN=$LAN)"; ip -o -4 addr show; exit 1; }
bridge "$WAN" tapwan
bridge "$LAN" taplan

DISK=/data/pfsense.qcow2
[ -f "$DISK" ] || qemu-img create -f qcow2 "$DISK" 8G
ISO=/data/install.iso
if [ ! -f "$ISO" ] && [ -f /iso/pfSense-CE-2.7.2-RELEASE-amd64.iso.gz ]; then
  gunzip -c /iso/pfSense-CE-2.7.2-RELEASE-amd64.iso.gz > "$ISO"
fi
CDROM=""; [ -f "$ISO" ] && CDROM="-cdrom $ISO"

ACCEL="-machine accel=tcg"; [ -c /dev/kvm ] && ACCEL="-enable-kvm -cpu host"
echo "pfSense VM: WAN=$WAN LAN=$LAN accel=${ACCEL%% *}"

websockify --web /usr/share/novnc 8006 127.0.0.1:5900 &
# e1000 -> em0 (WAN, first) / em1 (LAN): lab/pfsense tool expects WAN em0.
# shellcheck disable=SC2086
exec qemu-system-x86_64 $ACCEL -smp 2 -m "${PFSENSE_RAM:-1024}" \
  -drive file="$DISK",if=virtio,format=qcow2 $CDROM -boot order=cd \
  -netdev tap,id=wan,ifname=tapwan,script=no,downscript=no -device e1000,netdev=wan,mac=52:54:00:00:01:01 \
  -netdev tap,id=lan,ifname=taplan,script=no,downscript=no -device e1000,netdev=lan,mac=52:54:00:00:02:01 \
  -vnc 127.0.0.1:0 -display none -serial none
