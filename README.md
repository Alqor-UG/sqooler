# coquma-sim-spooler 

## Known issues
The `scp` action might tell you that it failed. This is not necessarily ture. This is a known issue with this GitHub action. In some cases it successfully copies the files in a tar archive unzips it and copies to the right target on destination. But the it fails to delete this tar file on the remote destination.
