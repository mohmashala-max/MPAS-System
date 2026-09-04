using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Mpas.Desktop;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        ApplicationConfiguration.Initialize();
        Application.Run(new MainForm());
    }
}

internal sealed class MainForm : Form
{
    private readonly HttpClient http = new();
    private readonly TextBox apiUrl = new() { Text = "http://localhost:8000/", Width = 260 };
    private readonly TextBox username = new() { Text = "demo", Width = 180 };
    private readonly TextBox password = new() { Text = "change-me", UseSystemPasswordChar = true, Width = 180 };
    private readonly TextBox facility = new() { Width = 180 };
    private readonly TextBox trap = new() { Width = 180 };
    private readonly TextBox imagePath = new() { Width = 300, ReadOnly = true };
    private readonly Label status = new() { AutoSize = true, Text = "Ready" };
    private readonly ListBox workOrders = new() { Width = 520, Height = 180 };
    private string? token;

    public MainForm()
    {
        Text = "M-PAS Field Desktop";
        Width = 620;
        Height = 620;
        StartPosition = FormStartPosition.CenterScreen;
        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(18), ColumnCount = 2, AutoSize = true };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        Add(layout, "API URL", apiUrl);
        Add(layout, "Username", username);
        Add(layout, "Password", password);
        var login = new Button { Text = "Sign in", AutoSize = true };
        login.Click += async (_, _) => await Login();
        Add(layout, "", login);
        Add(layout, "Facility ID", facility);
        Add(layout, "Trap ID", trap);
        var choose = new Button { Text = "Choose image", AutoSize = true };
        choose.Click += (_, _) => ChooseImage();
        Add(layout, "Image", choose);
        Add(layout, "", imagePath);
        var inspect = new Button { Text = "Upload and inspect", AutoSize = true, Enabled = false };
        inspect.Click += async (_, _) => await Inspect(inspect);
        Add(layout, "", inspect);
        var refresh = new Button { Text = "Refresh work orders", AutoSize = true, Enabled = false };
        refresh.Click += async (_, _) => await LoadWorkOrders();
        Add(layout, "", refresh);
        Add(layout, "Work orders", workOrders);
        layout.Controls.Add(status, 0, layout.RowCount);
        layout.SetColumnSpan(status, 2);
        Controls.Add(layout);
        login.Tag = (inspect, refresh);
    }

    private static void Add(TableLayoutPanel layout, string label, Control control)
    {
        var row = layout.RowCount++;
        layout.Controls.Add(new Label { Text = label, AutoSize = true, Anchor = AnchorStyles.Left }, 0, row);
        layout.Controls.Add(control, 1, row);
    }

    private void ChooseImage()
    {
        using var dialog = new OpenFileDialog { Filter = "Images|*.jpg;*.jpeg;*.png;*.webp" };
        if (dialog.ShowDialog() == DialogResult.OK) imagePath.Text = dialog.FileName;
    }

    private async Task Login()
    {
        try
        {
            var content = new FormUrlEncodedContent(new Dictionary<string, string> { ["username"] = username.Text, ["password"] = password.Text });
            var response = await http.PostAsync(Uri("api/v1/auth/token"), content);
            response.EnsureSuccessStatusCode();
            var json = JsonNode.Parse(await response.Content.ReadAsStringAsync())!;
            token = json["access_token"]!.GetValue<string>();
            status.Text = "Signed in. Ready for inspection.";
            SetActions(true);
        }
        catch (Exception error) { status.Text = $"Sign-in failed: {error.Message}"; }
    }

    private async Task Inspect(Button button)
    {
        if (token is null || string.IsNullOrWhiteSpace(facility.Text) || string.IsNullOrWhiteSpace(trap.Text) || string.IsNullOrWhiteSpace(imagePath.Text))
        {
            status.Text = "Facility, trap, and image are required.";
            return;
        }
        button.Enabled = false;
        try
        {
            using var imageContent = new StreamContent(File.OpenRead(imagePath.Text));
            imageContent.Headers.ContentType = new MediaTypeHeaderValue(ContentType(imagePath.Text));
            using var form = new MultipartFormDataContent();
            form.Add(imageContent, "image", Path.GetFileName(imagePath.Text));
            using var upload = await Authorized().PostAsync(Uri("api/v1/images"), form);
            upload.EnsureSuccessStatusCode();
            var stored = JsonNode.Parse(await upload.Content.ReadAsStringAsync())!["image_uri"]!.GetValue<string>();
            var payload = new { facility_id = facility.Text, trap_id = trap.Text, image_uri = stored, detections = Array.Empty<object>() };
            using var inspect = await Authorized().PostAsync(Uri("api/v1/ai/inspect"), JsonContent.Create(payload));
            inspect.EnsureSuccessStatusCode();
            status.Text = "Inspection completed.";
            await LoadWorkOrders();
        }
        catch (Exception error) { status.Text = $"Inspection failed: {error.Message}"; }
        finally { button.Enabled = true; }
    }

    private async Task LoadWorkOrders()
    {
        if (token is null || string.IsNullOrWhiteSpace(facility.Text)) return;
        try
        {
            using var response = await Authorized().GetAsync(Uri($"api/v1/facilities/{System.Uri.EscapeDataString(facility.Text)}/work-orders"));
            response.EnsureSuccessStatusCode();
            var items = JsonNode.Parse(await response.Content.ReadAsStringAsync())!.AsArray();
            workOrders.Items.Clear();
            foreach (var item in items) workOrders.Items.Add($"{item!["work_order_id"]} | {item["status"]} | {item["priority"]}");
        }
        catch (Exception error) { status.Text = $"Work orders failed: {error.Message}"; }
    }

    private HttpClient Authorized()
    {
        http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        return http;
    }

    private Uri Uri(string path) => new(new Uri(apiUrl.Text.EndsWith('/') ? apiUrl.Text : apiUrl.Text + '/'), path);
    private static string ContentType(string path) => Path.GetExtension(path).ToLowerInvariant() switch { ".png" => "image/png", ".webp" => "image/webp", _ => "image/jpeg" };
    private void SetActions(bool enabled)
    {
        foreach (Control control in Controls.OfType<TableLayoutPanel>().First().Controls)
            if (control is Button button && button.Text is "Upload and inspect" or "Refresh work orders") button.Enabled = enabled;
    }
}
