#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
#include <chrono>
#include <thread>

#ifdef _WIN32
#include <windows.h>
#endif

// Function to collect CPU and Memory metrics in cross-platform C++
std::string get_metrics_json() {
    double cpu_usage = 0.0;
    double mem_usage = 0.0;

#ifdef _WIN32
    // Windows fallback for local development
    MEMORYSTATUSEX memInfo;
    memInfo.dwLength = sizeof(MEMORYSTATUSEX);
    GlobalMemoryStatusEx(&memInfo);
    mem_usage = (double)memInfo.dwMemoryLoad;
    cpu_usage = 25.5; // Baseline simulation on Windows host
#else
    // Linux procfs scraping (/proc/stat & /proc/meminfo)
    std::ifstream meminfo("/proc/meminfo");
    if (meminfo.is_open()) {
        std::string line;
        long total_mem = 0, free_mem = 0, available_mem = 0;
        while (std::getline(meminfo, line)) {
            if (line.rfind("MemTotal:", 0) == 0) {
                std::sscanf(line.c_str(), "MemTotal: %ld kB", &total_mem);
            } else if (line.rfind("MemAvailable:", 0) == 0) {
                std::sscanf(line.c_str(), "MemAvailable: %ld kB", &available_mem);
            }
        }
        if (total_mem > 0) {
            mem_usage = ((double)(total_mem - available_mem) / total_mem) * 100.0;
        }
    }

    std::ifstream stat("/proc/stat");
    if (stat.is_open()) {
        std::string cpu_label;
        long user, nice, system, idle;
        stat >> cpu_label >> user >> nice >> system >> idle;
        long total = user + nice + system + idle;
        if (total > 0) {
            cpu_usage = ((double)(user + system) / total) * 100.0;
        }
    }
#endif

    auto now = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();

    std::stringstream ss;
    ss << "{\"cpu_percent\":" << cpu_usage
       << ",\"memory_percent\":" << mem_usage
       << ",\"timestamp_ms\":" << now << "}";
    return ss.str();
}

int main(int argc, char* argv[]) {
    // Single-shot run prints the JSON metric to stdout
    std::cout << get_metrics_json() << std::endl;
    return 0;
}