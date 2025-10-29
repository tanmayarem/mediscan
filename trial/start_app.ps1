# PowerShell script to start MedScan
# Load environment variables from .env file if it exists
if (Test-Path ..\.env) {
    Get-Content ..\.env | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $name = $matches[1]
            $value = $matches[2]
            Set-Content env:\$name $value
        }
    }
}

# Start the application
python app.py

