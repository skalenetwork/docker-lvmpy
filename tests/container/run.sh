set -e 
while true
do
    cd /data
    sudo rm -rf *
    echo "DarovaHop" >> 2.txt
    sleep 0.3 
    sudo btrfs subvolume create 'sub'
    sleep 0.2 
    sudo btrfs subvolume snapshot 'sub' 'snap-sub'
    sleep 0.2 
    sudo btrfs subvolume delete 'snap-sub'
    sleep 0.2 
    sudo btrfs subvolume delete 'sub'
done
