# random seed generator based on current datetime
# working with sh

n=$(date +%N | sed 's/^0*//')
[ -n "$n" ] || n=0
echo $((n % 900000000 + 1))