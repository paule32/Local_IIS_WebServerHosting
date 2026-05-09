using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.UseRouting();

app.MapGet("/debug", () => Results.Content(
    "<h1>Debug Route läuft</h1>",
    "text/html; charset=utf-8"
));

app.UseMiddleware<TimeWindowMiddleware>();

app.UseDefaultFiles();
app.UseStaticFiles();


app.MapGet("/", () => Results.Content(
    "<h1>IIS Time Window Gateway läuft</h1><p>Keine aktive Sperre gefunden.</p>",
    "text/html; charset=utf-8"
));

app.Run();


public class TimeWindowMiddleware
{
    private readonly RequestDelegate     _next;
    private readonly IWebHostEnvironment _env;

    public TimeWindowMiddleware(RequestDelegate next, IWebHostEnvironment env)
    {
        _next = next;
        _env = env;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        var hostName     = context.Request.Host.Host;
        var schedulePath = FindScheduleFile(context, hostName);

        Console.WriteLine($"Host: {hostName}");
        Console.WriteLine($"SchedulePath: {schedulePath}");

        if (context.Request.Path.StartsWithSegments("/debug"))
        {
            await _next(context);
            return;
        }
    
        if (!string.IsNullOrWhiteSpace(schedulePath) && File.Exists(schedulePath))
        {
            var schedule = await LoadScheduleAsync(schedulePath);
            var cell = GetCurrentCell(schedule);

            Console.WriteLine($"Cell: enabled={cell?.Enabled}, mode={cell?.Mode}");

            if (cell != null && cell.Enabled == 1)
            {
                var html = await BuildHtmlAsync(cell);

                context.Response.StatusCode = 503;
                context.Response.ContentType = "text/html; charset=utf-8";
                context.Response.Headers["Retry-After"] = "1800";

                await context.Response.WriteAsync(html);
                return;
            }
        }

        await _next(context);
    }

    private string FindScheduleFile(HttpContext context, string hostName)
    {
        var root = _env.WebRootPath;

        if (string.IsNullOrWhiteSpace(root))
            root = Directory.GetCurrentDirectory();

        var localSchedule = Path.Combine(root, ".schedule.json");

        if (File.Exists(localSchedule))
            return localSchedule;

        var safeHost = MakeSafeFileName(hostName);

        var centralSchedule = Path.Combine(
            Directory.GetCurrentDirectory(),
            "config",
            safeHost + ".schedule.json"
        );

        if (File.Exists(centralSchedule))
            return centralSchedule;

        return "";
    }

    private static string MakeSafeFileName(string value)
    {
        foreach (var ch in Path.GetInvalidFileNameChars())
            value = value.Replace(ch, '_');

        return value;
    }

    private static async Task<ScheduleFile?> LoadScheduleAsync(string path)
    {
        try
        {
            var json = await File.ReadAllTextAsync(path);

            return JsonSerializer.Deserialize<ScheduleFile>(
                json,
                new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                }
            );
        }
        catch (Exception ex)
        {
            Console.WriteLine(ex.ToString());
            return null;
        }
    }

    private static ScheduleCell? GetCurrentCell(ScheduleFile? schedule)
    {
        if (schedule?.AvailabilityGrid?.Grid == null)
            return null;

        var now = DateTime.Now;

        var dayIndex  = ((int)now.DayOfWeek + 6) % 7;
        var slotIndex = now.Hour * 2;

        if (now.Minute >= 30)
            slotIndex += 1;

        try
        {
            return schedule.AvailabilityGrid.Grid[dayIndex][slotIndex];
        }
        catch
        {
            return null;
        }
    }

    private static async Task<string> BuildHtmlAsync(ScheduleCell cell)
    {
        const string defaultHtml = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>Website temporarily unavailable</title>
</head>
<body>
    <h1>Website temporarily unavailable</h1>
    <p>Diese Website ist aktuell durch ein Zeitfenster gesperrt.</p>
</body>
</html>
""";

        if (cell.Mode == 1)
            return defaultHtml;

        if (cell.Mode == 2)
        {
            if (!string.IsNullOrWhiteSpace(cell.Path) && File.Exists(cell.Path))
            {
                try
                {
                    return await File.ReadAllTextAsync(cell.Path);
                }
                catch
                {
                    return defaultHtml;
                }
            }

            return defaultHtml;
        }

        if (cell.Mode == 3)
        {
            if (!string.IsNullOrWhiteSpace(cell.Text))
                return cell.Text;

            return defaultHtml;
        }

        return defaultHtml;
    }
}


public class ScheduleFile
{
    public string HostName { get; set; } = "";
    public AvailabilityGrid? AvailabilityGrid { get; set; }
}

public class AvailabilityGrid
{
    public string Date { get; set; } = "";
    public List<List<ScheduleCell>> Grid { get; set; } = new();
}

public class ScheduleCell
{
    public int Enabled { get; set; } = 0;
    public int Mode { get; set; } = 1;
    public string Path { get; set; } = "";
    public string Text { get; set; } = "";
}
