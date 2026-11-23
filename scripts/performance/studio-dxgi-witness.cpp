#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <d3d11.h>
#include <dxgi1_2.h>
#include <wrl/client.h>

#include <algorithm>
#include <array>
#include <cstdint>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>

using Microsoft::WRL::ComPtr;

constexpr unsigned markerBits = 40;
constexpr std::uint8_t markerSync = 0xd7;

struct Settings {
    std::wstring output;
    unsigned x = 0;
    unsigned y = 0;
    unsigned width = 0;
    unsigned height = 0;
    unsigned seconds = 0;
};

struct Output {
    ComPtr<IDXGIAdapter1> adapter;
    ComPtr<IDXGIOutput1> display;
    DXGI_OUTPUT_DESC desc;
};

struct Marker {
    const char* status;
    std::uint32_t sequence = 0;
    unsigned checksum = 0;
    unsigned expectedChecksum = 0;
};

void check(HRESULT status, const char* operation) {
    if (FAILED(status)) {
        throw std::runtime_error(std::string(operation) + " failed, HRESULT " + std::to_string(status));
    }
}

std::int64_t qpc() {
    LARGE_INTEGER now{};
    if (!QueryPerformanceCounter(&now)) throw std::runtime_error("Cannot read QPC.");
    return now.QuadPart;
}

std::int64_t qpcFrequency() {
    LARGE_INTEGER frequency{};
    if (!QueryPerformanceFrequency(&frequency) || frequency.QuadPart <= 0) {
        throw std::runtime_error("Cannot read the QPC frequency.");
    }
    return frequency.QuadPart;
}

unsigned unsignedArgument(std::wstring_view value) {
    if (value.empty() || value.size() > 6 || value.find_first_not_of(L"0123456789") != value.npos) {
        throw std::runtime_error("ROI and capture duration values must be unsigned integers.");
    }
    return std::stoul(std::wstring(value));
}

Settings arguments(int argc, wchar_t** argv) {
    if (argc != 14 || std::wstring_view(argv[1]) != L"--capture" ||
        std::wstring_view(argv[2]) != L"--output" || std::wstring_view(argv[4]) != L"--x" ||
        std::wstring_view(argv[6]) != L"--y" || std::wstring_view(argv[8]) != L"--width" ||
        std::wstring_view(argv[10]) != L"--height" || std::wstring_view(argv[12]) != L"--seconds") {
        throw std::runtime_error("Pass --capture --output DEVICE --x X --y Y --width WIDTH --height HEIGHT --seconds SECONDS, in that order.");
    }
    Settings settings{
        argv[3], unsignedArgument(argv[5]), unsignedArgument(argv[7]), unsignedArgument(argv[9]),
        unsignedArgument(argv[11]), unsignedArgument(argv[13]),
    };
    if (settings.output.empty() || settings.width < markerBits || settings.width > 320 ||
        settings.width % markerBits || !settings.height || settings.height > 64 ||
        !settings.seconds || settings.seconds > 120) {
        throw std::runtime_error("Use a 40–320 pixel width divisible by 40, height 1–64, and duration 1–120 seconds.");
    }
    return settings;
}

Output selectOutput(const std::wstring& name) {
    ComPtr<IDXGIFactory1> factory;
    check(CreateDXGIFactory1(IID_PPV_ARGS(factory.GetAddressOf())), "CreateDXGIFactory1");
    std::optional<Output> selected;
    for (UINT adapterIndex = 0;; ++adapterIndex) {
        ComPtr<IDXGIAdapter1> adapter;
        const HRESULT adapterResult = factory->EnumAdapters1(adapterIndex, adapter.GetAddressOf());
        if (adapterResult == DXGI_ERROR_NOT_FOUND) break;
        check(adapterResult, "EnumAdapters1");
        for (UINT outputIndex = 0;; ++outputIndex) {
            ComPtr<IDXGIOutput> output;
            const HRESULT outputResult = adapter->EnumOutputs(outputIndex, output.GetAddressOf());
            if (outputResult == DXGI_ERROR_NOT_FOUND) break;
            check(outputResult, "EnumOutputs");
            DXGI_OUTPUT_DESC desc{};
            check(output->GetDesc(&desc), "GetDesc");
            if (!desc.AttachedToDesktop || _wcsicmp(desc.DeviceName, name.c_str()) != 0) continue;
            if (selected) throw std::runtime_error("The display name matches multiple attached DXGI outputs.");
            ComPtr<IDXGIOutput1> display;
            check(output.As(&display), "Query IDXGIOutput1");
            selected = Output{adapter, std::move(display), desc};
        }
    }
    if (selected) return *selected;
    throw std::runtime_error("The requested device is not an attached DXGI output.");
}

std::string jsonDeviceName(std::wstring_view value) {
    std::string name;
    for (wchar_t character : value) {
        if (character < 32 || character > 126) throw std::runtime_error("Unexpected DXGI device name.");
        if (character == '\\' || character == '"') name += '\\';
        name += static_cast<char>(character);
    }
    return name;
}

std::uint8_t markerChecksum(const std::array<std::uint8_t, 5>& bytes) {
    std::uint8_t crc = 0;
    for (unsigned i = 0; i < 4; ++i) {
        crc ^= bytes[i];
        for (unsigned bit = 0; bit < 8; ++bit) {
            crc = static_cast<std::uint8_t>((crc << 1) ^ ((crc & 0x80) ? 0x07 : 0));
        }
    }
    return crc;
}

Marker decode(const D3D11_MAPPED_SUBRESOURCE& mapped, const Settings& settings) {
    std::array<std::uint8_t, 5> bytes{};
    const auto* base = static_cast<const std::uint8_t*>(mapped.pData);
    const unsigned cellWidth = settings.width / markerBits;
    for (unsigned bit = 0; bit < markerBits; ++bit) {
        const unsigned x = bit * cellWidth + cellWidth / 2;
        int cellValue = -1;
        for (unsigned y = 0; y < settings.height; ++y) {
            const auto* pixel = base + y * mapped.RowPitch + 4 * x;
            const auto levels = std::minmax({pixel[0], pixel[1], pixel[2]});
            const int value = levels.second <= 32 ? 0 : (levels.first >= 220 ? 1 : -1);
            if (value < 0 || (cellValue >= 0 && cellValue != value)) return {"ambiguous_pixels"};
            cellValue = value;
        }
        bytes[bit / 8] = static_cast<std::uint8_t>((bytes[bit / 8] << 1) | cellValue);
    }
    if (bytes[0] != markerSync) return {"wrong_sync"};
    const std::uint32_t sequence = (std::uint32_t{bytes[1]} << 16) |
                                   (std::uint32_t{bytes[2]} << 8) | bytes[3];
    const auto checksum = markerChecksum(bytes);
    return {checksum == bytes[4] ? "valid" : "wrong_checksum", sequence, bytes[4], checksum};
}

void testMarker() {
    const Settings settings{L"", 0, 0, 80, 1, 0};
    const std::array<std::uint8_t, 5> marker{0xd7, 0x12, 0x34, 0x56, 0xd3};
    std::array<std::uint8_t, 320> pixels{};
    for (unsigned bit = 0; bit < markerBits; ++bit) {
        const auto level = (marker[bit / 8] >> (7 - bit % 8)) & 1 ? std::uint8_t{255} : std::uint8_t{0};
        std::fill_n(pixels.data() + bit * 8, 8, level);
    }
    const D3D11_MAPPED_SUBRESOURCE map{pixels.data(), 320, 320};
    const auto result = decode(map, settings);
    if (std::string_view(result.status) != "valid" || result.sequence != 0x123456 || result.checksum != 0xd3) {
        throw std::runtime_error("The synthetic marker did not decode.");
    }
    std::fill_n(pixels.end() - 8, 8, std::uint8_t{0});
    if (std::string_view(decode(map, settings).status) != "wrong_checksum") {
        throw std::runtime_error("The synthetic checksum error was accepted.");
    }
    std::cout << "Synthetic ROI marker and checksum checks passed.\n";
}

Marker readMarker(ID3D11DeviceContext* context, ID3D11Texture2D* region, IDXGIResource* resource,
                  const Settings& settings, std::int64_t deadline) {
    ComPtr<ID3D11Texture2D> desktop;
    check(resource->QueryInterface(IID_PPV_ARGS(desktop.GetAddressOf())), "Query desktop texture");
    D3D11_BOX box{settings.x, settings.y, 0, settings.x + settings.width, settings.y + settings.height, 1};
    context->CopySubresourceRegion(region, 0, 0, 0, 0, desktop.Get(), 0, &box);
    context->Flush();
    while (qpc() < deadline) {
        D3D11_MAPPED_SUBRESOURCE map{};
        const HRESULT status = context->Map(region, 0, D3D11_MAP_READ, D3D11_MAP_FLAG_DO_NOT_WAIT, &map);
        if (status == DXGI_ERROR_WAS_STILL_DRAWING) {
            SwitchToThread();
            continue;
        }
        check(status, "Map marker region");
        const Marker marker = decode(map, settings);
        context->Unmap(region, 0);
        return marker;
    }
    return {"readback_timeout"};
}

int capture(const Settings& settings) {
    const auto output = selectOutput(settings.output);
    const auto bounds = output.desc.DesktopCoordinates;
    const auto width = static_cast<unsigned>(bounds.right - bounds.left);
    const auto height = static_cast<unsigned>(bounds.bottom - bounds.top);
    if (output.desc.Rotation != DXGI_MODE_ROTATION_IDENTITY || settings.x + settings.width > width ||
        settings.y + settings.height > height) {
        throw std::runtime_error("Select an unrotated output and a region inside its native pixel bounds.");
    }
    DXGI_ADAPTER_DESC1 adapter{};
    check(output.adapter->GetDesc1(&adapter), "Describe the output adapter");
    ComPtr<ID3D11Device> device;
    ComPtr<ID3D11DeviceContext> context;
    check(D3D11CreateDevice(output.adapter.Get(), D3D_DRIVER_TYPE_UNKNOWN, nullptr, 0, nullptr, 0,
                            D3D11_SDK_VERSION, device.GetAddressOf(), nullptr, context.GetAddressOf()),
          "D3D11CreateDevice");
    ComPtr<IDXGIOutputDuplication> duplication;
    check(output.display->DuplicateOutput(device.Get(), duplication.GetAddressOf()), "DuplicateOutput");
    DXGI_OUTDUPL_DESC desc{};
    duplication->GetDesc(&desc);
    if (desc.ModeDesc.Format != DXGI_FORMAT_B8G8R8A8_UNORM || desc.ModeDesc.Width != width ||
        desc.ModeDesc.Height != height) {
        throw std::runtime_error("The duplication output did not provide matching native BGRA8 pixels.");
    }
    D3D11_TEXTURE2D_DESC regionDesc{};
    regionDesc.Width = settings.width;
    regionDesc.Height = settings.height;
    regionDesc.MipLevels = regionDesc.ArraySize = regionDesc.SampleDesc.Count = 1;
    regionDesc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
    regionDesc.Usage = D3D11_USAGE_STAGING;
    regionDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    ComPtr<ID3D11Texture2D> region;
    check(device->CreateTexture2D(&regionDesc, nullptr, region.GetAddressOf()), "Create marker region");
    const auto frequency = qpcFrequency();
    const auto start = qpc();
    const auto end = start + frequency * settings.seconds;
    std::cout << "{\"type\":\"capture\",\"schema\":\"studio-dxgi-roi-v1\",\"output\":\""
              << jsonDeviceName(output.desc.DeviceName) << "\",\"adapterLuidHigh\":"
              << adapter.AdapterLuid.HighPart << ",\"adapterLuidLow\":" << adapter.AdapterLuid.LowPart
              << ",\"outputLeft\":" << bounds.left << ",\"outputTop\":" << bounds.top
              << ",\"outputWidth\":" << width << ",\"outputHeight\":" << height
              << ",\"refreshNumerator\":" << desc.ModeDesc.RefreshRate.Numerator
              << ",\"refreshDenominator\":" << desc.ModeDesc.RefreshRate.Denominator
              << ",\"x\":" << settings.x << ",\"y\":" << settings.y
              << ",\"width\":" << settings.width << ",\"height\":" << settings.height
              << ",\"qpcFrequency\":\"" << frequency << "\",\"startQpc\":\"" << start
              << "\",\"deadlineQpc\":\"" << end << "\",\"certified\":false}\n" << std::flush;

    unsigned desktopFrames = 0, mouseOnly = 0, valid = 0, inconsistent = 0;
    std::uint64_t missed = 0;
    while (true) {
        const auto now = qpc();
        if (now >= end) break;
        const auto timeout = static_cast<UINT>(std::clamp((end - now) * 1000 / frequency,
                                                          std::int64_t{1}, std::int64_t{32}));
        DXGI_OUTDUPL_FRAME_INFO info{};
        ComPtr<IDXGIResource> resource;
        const HRESULT status = duplication->AcquireNextFrame(timeout, &info, resource.GetAddressOf());
        if (status == DXGI_ERROR_WAIT_TIMEOUT) continue;
        check(status, "AcquireNextFrame");
        const auto acquired = qpc();
        if (acquired >= end) {
            check(duplication->ReleaseFrame(), "ReleaseFrame");
            break;
        }
        try {
            Marker marker{"mouse_only"};
            if (info.LastPresentTime.QuadPart) {
                ++desktopFrames;
                if (info.AccumulatedFrames > 1) missed += info.AccumulatedFrames - 1;
                if (!info.AccumulatedFrames) ++inconsistent;
                marker = info.ProtectedContentMaskedOut
                    ? Marker{"protected_content"}
                    : readMarker(context.Get(), region.Get(), resource.Get(), settings,
                                 std::min(end, acquired + frequency * 3 / 1000));
                if (std::string_view(marker.status) == "valid") ++valid;
            } else {
                ++mouseOnly;
                if (info.AccumulatedFrames) ++inconsistent;
            }
            std::cout << "{\"type\":\"frame\",\"acquiredQpc\":\"" << acquired
                      << "\",\"lastPresentQpc\":\"" << info.LastPresentTime.QuadPart
                      << "\",\"lastMouseUpdateQpc\":\"" << info.LastMouseUpdateTime.QuadPart
                      << "\",\"accumulatedFrames\":" << info.AccumulatedFrames
                      << ",\"status\":\"" << marker.status << '"';
            if (std::string_view(marker.status) == "valid" || std::string_view(marker.status) == "wrong_checksum") {
                std::cout << ",\"sequence\":" << marker.sequence << ",\"checksum\":" << marker.checksum
                          << ",\"expectedChecksum\":" << marker.expectedChecksum;
            }
            std::cout << "}\n";
        } catch (...) {
            duplication->ReleaseFrame();
            throw;
        }
        check(duplication->ReleaseFrame(), "ReleaseFrame");
    }
    std::cout << "{\"type\":\"summary\",\"endQpc\":\"" << qpc() << "\",\"desktopFrames\":"
              << desktopFrames << ",\"mouseOnly\":" << mouseOnly << ",\"validMarkers\":" << valid
              << ",\"knownMissedDesktopUpdates\":" << missed
              << ",\"inconsistentAccumulation\":" << inconsistent << ",\"certified\":false}\n";
    return desktopFrames && valid == desktopFrames && !missed && !inconsistent ? 0 : 2;
}

int wmain(int argc, wchar_t** argv) {
    if (argc == 1 || (argc == 2 && std::wstring_view(argv[1]) == L"--help")) {
        std::cout << "studio-dxgi-witness --capture --output DEVICE --x X --y Y --width WIDTH --height HEIGHT --seconds SECONDS\n"
                     "DEVICE is a DXGI output name, such as \\\\.\\DISPLAY1. X and Y are native pixels relative to that output.\n"
                     "Use an isolated calibration view with a 40-cell horizontal marker. Read cells left to right, MSB first:\n"
                     "0xd7, 24-bit sequence (big-endian), CRC-8/ATM (poly 0x07, init 0) of the first four bytes.\n"
                     "Mark each cell white for 1 or black for 0 across the selected height. Set WIDTH to 40 times the cell width.\n"
                     "Writes only JSON Lines metadata. No image file is created. Exit 2 means the marker coverage was incomplete.\n"
                     "The witness alone does not certify Studio canvas frames or actual display cadence.\n";
        return 0;
    }
    try {
        if (argc == 2 && std::wstring_view(argv[1]) == L"--self-test") {
            testMarker();
            return 0;
        }
        return capture(arguments(argc, argv));
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
