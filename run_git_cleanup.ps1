# Ensure git-filter-repo is installed via pip (pip install git-filter-repo)
git filter-repo --path "AEGIS_Radar.exe" --path "full_log.txt" --path "*.log" --invert-paths --force
Write-Host "Git history cleaned successfully!"
