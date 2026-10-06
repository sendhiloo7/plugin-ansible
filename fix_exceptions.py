import re
import sys

with open("src/main/java/io/kestra/plugin/ansible/runner/AnsibleRunner.java", "r") as f:
    content = f.read()

# F7: Playbooks copy error
content = re.sub(
    r'FileUtils\.copyDirectory\(playbooksDir\.toFile\(\), projectDir\.toFile\(\)\);\n\s+\} catch \(Exception ignored\) \{\}',
    r'FileUtils.copyDirectory(playbooksDir.toFile(), projectDir.toFile());\n            } catch (Exception e) { runContext.logger().warn("Failed to copy playbooks directory: {}", e.getMessage()); }',
    content
)

# F7: Inventory auto detect 1
content = re.sub(
    r'runContext\.logger\(\)\.info\("Using auto-detected inventory directory: \{\}", inventoryFolder\);\n\s+return;\n\s+\}\n\s+\}\n\s+\}\n\s+\} catch \(Exception ignored\) \{\}',
    r'runContext.logger().info("Using auto-detected inventory directory: {}", inventoryFolder);\n                        return;\n                    }\n                }\n            } catch (Exception e) { runContext.logger().warn("Failed auto-detect inventory: {}", e.getMessage()); }',
    content
)

# F7: Inventory auto detect 2
content = re.sub(
    r'runContext\.logger\(\)\.info\("Using auto-detected inventory directory: \{\}", inventoriesFolder\);\n\s+return;\n\s+\}\n\s+\}\n\s+\}\n\s+\} catch \(Exception ignored\) \{\}',
    r'runContext.logger().info("Using auto-detected inventory directory: {}", inventoriesFolder);\n                        return;\n                    }\n                }\n            } catch (Exception e) { runContext.logger().warn("Failed auto-detect inventories: {}", e.getMessage()); }',
    content
)

# F7: makeExecutable
content = re.sub(
    r'\}\n\s+\} catch \(IOException ignored\) \{\}',
    r'}\n        } catch (IOException e) { throw new RuntimeException("Failed to make executable", e); }',
    content
)

# F7: read status
content = re.sub(
    r'status = Files\.readString\(statusFile, StandardCharsets\.UTF_8\)\.trim\(\);\n\s+\} catch \(IOException ignored\) \{\}',
    r'status = Files.readString(statusFile, StandardCharsets.UTF_8).trim();\n                } catch (IOException e) { throw new RuntimeException("Failed to read status file", e); }',
    content
)

# F7: read rc
content = re.sub(
    r'rc = Integer\.parseInt\(Files\.readString\(rcFile, StandardCharsets\.UTF_8\)\.trim\(\)\);\n\s+\} catch \(Exception ignored\) \{\}',
    r'rc = Integer.parseInt(Files.readString(rcFile, StandardCharsets.UTF_8).trim());\n                } catch (Exception e) { throw new RuntimeException("Failed to read rc file", e); }',
    content
)

# F7: list job_events dir
content = re.sub(
    r'\s+\} catch \(IOException ignored\) \{\}\n\s+\}\n\s+\}\n\n\s+return new ExecutionTelemetry',
    r'\n                } catch (IOException e) { throw new RuntimeException("Failed to list job_events dir", e); }\n            }\n        }\n\n        return new ExecutionTelemetry',
    content
)

# Limit stats size
content = content.replace(
    'stats.put(h, hStat);',
    'if (stats.size() < 1000) stats.put(h, hStat);'
)

with open("src/main/java/io/kestra/plugin/ansible/runner/AnsibleRunner.java", "w") as f:
    f.write(content)
