ip_file=$1
machines=($(cat $ip_file))
nservers=${#machines[@]}

i=0
while [ $i -lt $nservers ]
do
	    echo $i ${machines[i]}
	        #ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 ${machines[i]} "sudo pkill -f varuna.launcher" 
		    echo "try to kill"
		        gcloud compute ssh ${machines[i]} --zone us-west1-a --command "bash /home/fot/adaptdl/examples/benchmarks/kill_all.sh" -- -o ConnectTimeout=60

			    i=$(($i+1))
		    done
