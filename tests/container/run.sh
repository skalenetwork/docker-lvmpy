set -e
while true
do
    cd /data
    echo "Removing all from data"
    sudo rm -f 2.txt
    echo "DarovaHop" >> 2.txt
    sleep 0.5
    if [ -e 'snap-sub' ]; then
	echo "Deleting snapshot volume"
	sudo btrfs subvolume delete 'snap-sub'
	sleep 0.5
    fi
    if [ -e 'sub' ]; then
	echo "Deleting original volume"
	sudo btrfs subvolume delete 'sub'
	sleep 0.5
    fi
    echo "Creating volume"
    sudo btrfs subvolume create 'sub'
    sleep 0.5
    echo "Creating snapshot volume"
    sudo btrfs subvolume snapshot 'sub' 'snap-sub'
    echo "Iteration finished"
done
