echo 'Disable docker-lvmpy service'
systemctl disable docker-lvmpy
echo 'Removing all volumes from schain volume group'
lvremove schains --yes
echo 'Removing volume group schain'
vgremove schains
echo 'Cleaning up /dev/loop0'
pvremove /dev/loop0
echo 'Unmount /dev/loop0'
umount /dev/loop0
echo 'Removing /dev/loop0'
losetup -d /dev/loop0
echo 'Removing loopbackfile.img'
rm -f loopbackfile.img
