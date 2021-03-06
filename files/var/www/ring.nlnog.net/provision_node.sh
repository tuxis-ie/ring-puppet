#!/bin/bash
#
# provision_node.sh - Provision an NLNOG RING node

ID=$1
OWNER=`echo $ID | sed -e 's/..$//'`

if [ ! "$ID" ];
then
	>&2 echo "$0 <node id>"
	exit 1
fi

echo "Provisioning $ID (owner: $OWNER)... "

declare -a commands=(
"echo \"$ID.ring.nlnog.net\" > /etc/hostname"
"hostname -F /etc/hostname"
"echo \"95.211.149.24   master01 master01.infra.ring.nlnog.net puppet\" >> /etc/hosts"
"echo \"2001:1AF8:4013::24 master01 master01.infra.ring.nlnog.net puppet\" >> /etc/hosts"
"apt-get update"
"apt-get -y install curl"
"curl https://ring.nlnog.net/ring.key | apt-key add -"
"curl https://ring.nlnog.net/sources.list > /etc/apt/sources.list"
"apt-get update"
"apt-get -y dist-upgrade"
"apt-get -y install puppet puppet-common"
)

for i in "${commands[@]}"
do
	echo "> $i"
	eval "$i"
	if [ $? == 1 ];
	then
		exit 1
	fi
done

puppetcommand="puppetd --test"
maxruns=5
run=1
echo "> $puppetcommand ($run)"
eval "$puppetcommand"
while [ $? -ne 0 -a $run -lt $maxruns ];
do
	run=$(( $run + 1 ))
	echo "> $puppetcommand ($run)"
	eval "$puppetcommand"
done
if [ $? -ne 0 -a $run -eq $maxruns ];
then
	>&2 echo "Failed to complete puppet run"
	exit 1
fi
echo "Done."

# puppetd --test; puppetd --test; puppetd --test
# passwd --delete root
# deluser --remove-home nlnog
# reboot

