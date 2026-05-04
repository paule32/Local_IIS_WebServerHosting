Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = "PowerShell GUI"
$form.Width = 500
$form.Height = 300
$form.StartPosition = "CenterScreen"

$label = New-Object System.Windows.Forms.Label
$label.Text = "Name:"
$label.Location = New-Object System.Drawing.Point(20, 30)
$label.AutoSize = $true
$form.Controls.Add($label)

$textbox = New-Object System.Windows.Forms.TextBox
$textbox.Location = New-Object System.Drawing.Point(80, 25)
$textbox.Width = 250
$form.Controls.Add($textbox)

$button = New-Object System.Windows.Forms.Button
$button.Text = "OK"
$button.Location = New-Object System.Drawing.Point(80, 70)
$button.Width = 100

$button.Add_Click({
    [System.Windows.Forms.MessageBox]::Show(
        "Hallo " + $textbox.Text,
        "Info"
    )
})

$form.Controls.Add($button)

[void]$form.ShowDialog()
