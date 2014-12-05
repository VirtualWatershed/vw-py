#!/bin/bash
# temperature_experiment.bash
#
# This script runs every step required for running the an experiment. The 
# experiment's hypothesis is that snow melting in the ISNOBAL model will be 
# accelerated so that snow melts sooner when the temperature is increased 
# throughout the water year.
#
# We'll do that by first downloading the required files and re-scaling them 
# with our quantization routine, then modifying every hour's worth of data's 
# temperature measurements by adding increasing multiples of 0.5 deg C up to
# 4.0. Then we run the ISNOBAL model on the re-scaled observed data as well as
# all our modified data. To visualize the melt, we finally read all the output
# data, sum the melt over all grid elements, save that to a csv for later use,
# and plot the 3-day summed, resampled melt data.
#
# Dependencies: GNU Paralell. On OS X with Homebrew installed 
# (http://brew.sh/): 
# $ brew install parallel 
#
# On Ubuntu/Debian (second command for proper compatability): 
# $ sudo apt-get install parallel && sudo rm /etc/parallel/config
# 
# To do this, we first have to download and re-scale the original input data 
# obtained from the icewater FTP site at Boise State University:

# Download data from ftp site (faster and more reliable than getting whole .zip)
function make_full_addr {
    filenum=$1

    root_ftp="ftp://icewater.boisestate.edu/boisefront-products/other/projects/Kormos_iSNOBAL/input.dp/"

    if [ $filenum -lt 10 ]; then
        filenum="000$filenum"
    elif [ $filenum -lt 100 ]; then
        filenum="00$filenum"
    elif [ $filenum -lt 1000 ]; then
        filenum="0$filenum"
    fi

    echo "${root_ftp}in.$filenum"
}

export -f make_full_addr

rm -f *.tmp

# CHANGE FOR FULL toggle comments between 11/8758 to do test/full experiment
for fnum in $(/usr/bin/seq 0 11); do
#for fnum in $(/usr/bin/seq 0 8758); do
    # these are the FTP addresses for the input files
    make_full_addr $fnum >> addr.tmp
    # make a file containing the expected 'in.0010' type names 
    make_full_addr $fnum | sed 's/.*\///' >> expected.tmp
done

# Download input files

full_save_dir=data/original_inputs

mkdir -p $full_save_dir

printf "\nDownloading input files\n"

parallel --verbose -a addr.tmp curl {} -o $full_save_dir/{/} 

printf "\n*** Done downloading input files. Restarting failed attempts ***\n"

# some files will invariably fail to download; this makes sure we miss none
ls data/original_inputs | sed 's/.*\///' > downloaded.tmp
comm -3 expected.tmp downloaded.tmp > missing.tmp
num_missing=$(wc -l missing.tmp | sed 's/ missing.tmp//')
root_ftp="ftp://icewater.boisestate.edu/boisefront-products/other/projects/Kormos_iSNOBAL"

while [ $num_missing -gt 0 ]; do
    
    for base_f in $(cat missing.tmp); do
        curl $root_ftp/input.dp/$base_f -o data/original_inputs/$base_f
    done

    ls data/original_inputs | sed 's/.*\///' > downloaded.tmp
    comm -3 expected.tmp downloaded.tmp > missing.tmp
    num_missing=$(wc -l missing.tmp | sed 's/ missing.tmp//')
    echo $num_missing
done

save_dir=data

printf "\nDownloading init, DEM, mask, and ppt_desc files\n"

curl $root_ftp/init.ipw -o $save_dir/init.ipw
curl $root_ftp/tl2p5_dem.ipw -o $save_dir/tl2p5_dem.ipw
curl $root_ftp/tl2p5mask.ipw -o $save_dir/tl2p5mask.ipw
curl $root_ftp/ppt_desc -o $save_dir/ppt_desc

mkdir -p $save_dir/ppt_images_dist

printf "\nDownloading precipitation events\n"

# CHANGE FOR FULL comment out 'head -n11' for a full run
cut -f2 $save_dir/ppt_desc | \
    head -n11 |\
    parallel basename |\
    parallel curl $root_ftp/ppt_images_dist/{} -o $save_dir/ppt_images_dist/{}

# now re-download all failed attempts for the precip ppt_images files
head -n11 data/ppt_desc | sed 's/.*\///' > expected.tmp
#cat data/ppt_desc | sed 's/.*\///' > expected.tmp
ls data/ppt_images_dist | sort -t"_" -k2g > downloaded.tmp
comm -3 expected.tmp downloaded.tmp > missing.tmp
num_missing=$(wc -l missing.tmp | sed 's/ missing.tmp//')
root_ftp="ftp://icewater.boisestate.edu/boisefront-products/other/projects/Kormos_iSNOBAL"
while [ $num_missing -gt 0 ]; do
    
    for base_f in $(cat missing.tmp); do
        curl $root_ftp/ppt_images_dist/$base_f -o data/ppt_images_dist/$base_f
    done

    ls data/ppt_images_dist | sort -t"_" -k2g > downloaded.tmp
    comm -3 expected.tmp downloaded.tmp > missing.tmp
    num_missing=$(wc -l missing.tmp | sed 's/ missing.tmp//')
    echo $num_missing
done

# one final wrinkle, on partial run 
# we need to modify the file names to match our setup in the ppt_desc file
# CHANGE FOR FULL toggle next three statements' comments for test/full
file_nums=$(ls data/ppt_images_dist | \
            egrep -o "_[0-9]+" | \
            sed 's/_//' | \
            sort -n)

# re-write data/ppt_desc with the sorted files
rm -f data/ppt_desc

for num in $file_nums; do
    printf "$num\tdata/ppt_images_dist/ppt4b_$num.ipw\n" >> data/ppt_desc
done


# Now that we've downloaded all the files, we re-quantize the data
# Data gets saved to 'data/inputs', defined in the python script
rm -f data/inputs/*
rm -rf data/inputsP*

find data/original_inputs -type f | parallel python recalc_input_headers.py

# CHANGE FOR FULL Comment out or remove these next two for loops for a full run
input_nums=$(ls data/inputs | egrep -o "[0-9]{2}$")

for fnum in $input_nums; do
    printf "mv data/inputs/in.00$fnum data/inputs/in.$fnum\n"
    mv "data/inputs/in.00$fnum" "data/inputs/in.$fnum"
done


# Increase the temperatures by multiples of .5 degrees
for mod_val in 0.5 1.0 1.5 2.0 2.5 3.0 3.5 4.0; do
    parallel python modify_ipw_temps.py $mod_val {} ::: $(find data/inputs -type f)
done


# Now we're ready to run ISNOBAL on each of our nine input scenarios: observed
# and each of the eight increasing temperature scenarios. modify_ipw_temps.py
# saved our modified data in folders like data/inputsP1.0 for the data that had
# it's temperature increased by 1.0. Run these like so:

parallel python run_isnobal.py data/inputsP{} data/outputsP{} ::: 0.5 1.0 1.5 2.0 2.5 3.0 3.5 4.0

python run_isnobal.py data/inputs data/outputs

# Let's do one more time-intensive procedure, then it's time to have some fun 
# and see if melting really was different for different temperature scenarios.
# First, let's make a CSV file of the sum of the snow melt for each hour over
# all grid points in the image using the nice properties of pandas resample
# function.

python create_summary_csv.py

# Plot our results
python plot_results.py

rm *.tmp
