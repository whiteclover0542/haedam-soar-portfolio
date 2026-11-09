# pfSense CE 2.7.2 VM inside a container (QEMU/KVM). See infra/pfsense/INSTALL.md.
FROM alpine:3.20
RUN apk add --no-cache qemu-system-x86_64 qemu-img iproute2 novnc websockify
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
VOLUME /data
EXPOSE 8006
ENTRYPOINT ["/entrypoint.sh"]
