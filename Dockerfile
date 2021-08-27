FROM dsarchive/dsa_common

# Add our code as another girder plugin
RUN cd /opt && \
    git clone https://github.com/DigitalSlideArchive/DSA-WSI-DeID.git && \
    cd DSA-WSI-DeID && \
    pip install -e .

# Build the girder client
RUN girder build --dev && \
    # Get rid of unnecessary files to keep the docker image smaller \
    find /opt -xdev -name node_modules -exec rm -rf {} \+ && \
    rm -rf /tmp/* ~/.npm
