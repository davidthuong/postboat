# Xuat nhom phan phoi tu mot tenant Microsoft 365 cho `postboat.py lists`.
#
# Chay tren may Windows co module ExchangeOnlineManagement (Install-Module
# ExchangeOnlineManagement), bang tai khoan admin cua tenant nguon:
#
#     powershell -ExecutionPolicy Bypass -File m365-lists-export.ps1
#
# Ket qua, ghi canh file script:
#   groups-m365.csv          moi distribution group mot dong (ke ca nhom rong)
#   lists-m365.csv           distribution group + thanh vien (List/ListName/Member/MemberType)
#   lists-m365-unified.csv   Microsoft 365 Group + thanh vien, cung bon cot
#
# Roi:  python3 postboat.py lists groups-m365.csv lists-m365.csv lists-m365-unified.csv
#
# Khong can them quyen nao cho app Entra: day la Exchange Online PowerShell,
# dang nhap bang nguoi (trinh duyet). Tenant khong co distribution group nao
# thi file tuong ung chi co BOM -- postboat.py lists hieu la 0 nhom.
$ErrorActionPreference = "Continue"
$out = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Output ("[{0}] bat dau" -f (Get-Date -Format "HH:mm:ss"))

try {
    $params = (Get-Command Connect-ExchangeOnline).Parameters
    if ($params.ContainsKey('DisableWAM')) {
        # Chay tu tien trinh khong co cua so (script, scheduler) thi WAM chet
        # voi "A window handle must be configured"; -DisableWAM roi ve trinh duyet.
        Connect-ExchangeOnline -ShowBanner:$false -DisableWAM
    } else {
        Connect-ExchangeOnline -ShowBanner:$false
    }
} catch {
    Write-Output ("[LOI] Connect-ExchangeOnline: {0}" -f $_.Exception.Message)
    exit 2
}
Write-Output ("[{0}] da ket noi: {1}" -f (Get-Date -Format "HH:mm:ss"), (Get-OrganizationConfig).Name)

$groups = Get-DistributionGroup -ResultSize Unlimited
Write-Output ("distribution groups: {0}" -f @($groups).Count)
$groups | Select-Object PrimarySmtpAddress, DisplayName, GroupType, RecipientTypeDetails, ManagedBy |
    Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $out "groups-m365.csv")

$rows = foreach ($g in $groups) {
    Get-DistributionGroupMember -Identity $g.Identity -ResultSize Unlimited |
        Select-Object @{n='List';e={$g.PrimarySmtpAddress}},
                      @{n='ListName';e={$g.DisplayName}},
                      @{n='Member';e={$_.PrimarySmtpAddress}},
                      @{n='MemberType';e={$_.RecipientTypeDetails}}
}
$rows | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $out "lists-m365.csv")
Write-Output ("distribution group member rows: {0}" -f @($rows).Count)

$unified = Get-UnifiedGroup -ResultSize Unlimited -ErrorAction SilentlyContinue
Write-Output ("microsoft 365 groups: {0}" -f @($unified).Count)
$urows = foreach ($g in $unified) {
    Get-UnifiedGroupLinks -Identity $g.Identity -LinkType Members -ResultSize Unlimited |
        Select-Object @{n='List';e={$g.PrimarySmtpAddress}},
                      @{n='ListName';e={$g.DisplayName}},
                      @{n='Member';e={$_.PrimarySmtpAddress}},
                      @{n='MemberType';e={$_.RecipientTypeDetails}}
}
$urows | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $out "lists-m365-unified.csv")
Write-Output ("microsoft 365 group member rows: {0}" -f @($urows).Count)

Disconnect-ExchangeOnline -Confirm:$false
Write-Output ("[{0}] xong -- dua ba file .csv cho postboat.py lists" -f (Get-Date -Format "HH:mm:ss"))
