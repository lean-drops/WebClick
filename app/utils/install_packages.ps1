# Definieren Sie die Pakete und deren Versionen
$packages = @(
    "puppeteer-extra",
    "puppeteer-extra-plugin-stealth",
    "puppeteer-extra-plugin-adblocker"
)

# Verzeichnis für das Herunterladen der Pakete erstellen
$downloadDir = "npm_packages"
New-Item -ItemType Directory -Force -Path $downloadDir

# Pakete herunterladen und installieren
foreach ($package in $packages) {
    Write-Host "Downloading and installing package: $package"
    
    # Paket herunterladen
    $packageFile = npm pack $package --registry https://registry.npmmirror.com/ -q -C $downloadDir
    
    # Paket installieren
    npm install "$downloadDir\$packageFile"
}

# Download-Verzeichnis löschen
Remove-Item -Recurse -Force $downloadDir

Write-Host "Installation completed successfully."
