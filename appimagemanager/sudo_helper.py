"""
AppImage Manager - Sudo Helper
Provides utilities for running commands with elevated privileges using pkexec.
"""

import subprocess
import logging
import os
import shutil # Keep for shutil.which
import tempfile

from .i18n import get_translator

logger = logging.getLogger(__name__)
translator = get_translator()

# --- Remove old functions (get_sudo_password_qt, create_helper_script, execute_script_with_privileges, cleanup_script) ---

def run_command_with_pkexec(cmd_list):
    """Executes a given command list with elevated privileges using pkexec.

    Args:
        cmd_list (list): The command and its arguments as a list of strings.
                         Example: ["mkdir", "-p", "/some/path"]

    Returns:
        tuple: (success_bool, output_str)
               success_bool is True if the command exits with 0, False otherwise.
               output_str contains combined stdout and stderr.
    """
    if not cmd_list:
        logger.error("Cannot execute command: Empty command list provided.")
        return False, "Empty command list"

    if not shutil.which("pkexec"):
        logger.error("Failed to execute command: 'pkexec' not found in PATH. Is policykit-1 installed?")
        return False, "'pkexec' command not found."

    # Prepend pkexec to the command list
    full_command = ["pkexec"] + cmd_list
    
    command_str_for_log = ' '.join(cmd_list) # Log command without pkexec for clarity
    logger.info(f"Executing with pkexec: {command_str_for_log}")
    logger.debug(f"Full command: {full_command}")

    try:
        # Use subprocess.run to wait for completion
        result = subprocess.run(
            full_command,
            capture_output=True, # Capture stdout and stderr
            text=True,
            encoding='utf-8',
            check=False # Don't raise exception on non-zero exit code
        )

        success = (result.returncode == 0)
        # Combine stdout and stderr for output
        output = ""
        if result.stdout:
            output += result.stdout.strip() + "\n"
        if result.stderr:
            output += result.stderr.strip()
        output = output.strip()
        
        logger.debug(f"pkexec command [' {command_str_for_log} '] finished. RC={result.returncode}. Output:\n---\n{output}\n---")

        if not success:
             logger.error(f"pkexec command [' {command_str_for_log} '] failed. RC={result.returncode}.")
        else:
            logger.info(f"pkexec command [' {command_str_for_log} '] return code indicates success (RC=0).")

        return success, output

    except FileNotFoundError: # Should be caught by shutil.which, but for safety
        logger.error("Failed to execute command: 'pkexec' not found (double check).")
        return False, "'pkexec' command not found."
    except Exception as e:
        logger.error(f"Unexpected error executing command [' {command_str_for_log} '] with pkexec: {e}", exc_info=True)
        error_message = f"Unexpected error: {e}"
        if "authenticate" in str(e).lower() or "cancel" in str(e).lower():
             error_message = translator.get_text("Authentication cancelled or failed.")
        return False, error_message

def run_commands_with_pkexec_script(command_list):
    """Executes multiple commands with a single pkexec call by creating a bash script.
    
    Args:
        command_list (list): List of command lists to execute.
                             Example: [["mkdir", "-p", "/some/path"], ["cp", "source", "dest"]]
    
    Returns:
        tuple: (success_bool, output_str)
               success_bool is True if all commands exit with 0, False otherwise.
               output_str contains combined stdout and stderr.
    """
    if not command_list:
        logger.error("Cannot execute commands: Empty command list provided.")
        return False, "Empty command list"

    if not shutil.which("pkexec"):
        logger.error("Failed to execute commands: 'pkexec' not found in PATH. Is policykit-1 installed?")
        return False, "'pkexec' command not found."
    
    try:
        # Create a temporary script file
        script_fd, script_path = tempfile.mkstemp(prefix="aim_pkexec_", suffix=".sh")
        script_content = "#!/bin/bash\n\n"
        script_content += "set -e\n\n" # Exit on error
        
        # Add log functions
        script_content += "log_cmd() {\n  echo \"Executing: $1\"\n}\n\n"
        
        # Convert each command list to a bash command and add to script
        command_count = 0
        for cmd in command_list:
            if not cmd:
                continue
            
            # Special handling for sed commands
            if cmd and len(cmd) >= 3 and cmd[0] == "sed" and cmd[1] == "-i":
                # This is a sed -i command, make sure it's properly quoted for bash script
                sed_pattern = cmd[2]
                target_file = cmd[3] if len(cmd) > 3 else ""
                
                # Properly escape the sed pattern for bash
                script_content += f"log_cmd 'sed -i \"{sed_pattern}\" {target_file}'\n"
                script_content += f"sed -i \"{sed_pattern}\" {target_file}\n\n"
            else:
                # Special handling for commands with || (OR operator)
                if "||" in cmd:
                    # Find the index of "||"
                    or_index = cmd.index("||")
                    # Split the command into main part and fallback
                    main_cmd = cmd[:or_index]
                    fallback = cmd[or_index+1:]
                    
                    # Handle main command and fallback separately
                    main_str = " ".join([f'"{arg}"' if ' ' in arg else arg for arg in main_cmd])
                    fallback_str = " ".join([f'"{arg}"' if ' ' in arg else arg for arg in fallback])
                    
                    # Combine with the || operator
                    cmd_str = f"{main_str} || {fallback_str}"
                else:
                    # Convert command list to a valid bash command string with proper quoting
                    cmd_str = " ".join([f'"{arg}"' if ' ' in arg or '*' in arg else arg for arg in cmd])
                
                # Add command to script with logging
                script_content += f"log_cmd '{cmd_str}'\n"
                script_content += f"{cmd_str}\n\n"
                
            command_count += 1
        
        # Write script content to file
        with os.fdopen(script_fd, 'w') as f:
            f.write(script_content)
        
        # Make script executable
        os.chmod(script_path, 0o700)
        logger.debug(f"Created temporary script with {command_count} commands: {script_path}")
        
        # Execute script with pkexec
        logger.info(f"Executing script with pkexec: {script_path}")
        result = subprocess.run(
            ["pkexec", script_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=False
        )
        
        success = (result.returncode == 0)
        # Combine stdout and stderr for output
        output = ""
        if result.stdout:
            output += result.stdout.strip() + "\n"
        if result.stderr:
            output += result.stderr.strip()
        output = output.strip()
        
        logger.debug(f"pkexec script execution finished. RC={result.returncode}. Output:\n---\n{output}\n---")
        
        if not success:
            logger.error(f"pkexec script execution failed. RC={result.returncode}.")
        else:
            logger.info(f"pkexec script execution successful (RC=0).")
        
        # Clean up the temporary script
        try:
            os.unlink(script_path)
            logger.debug(f"Removed temporary script: {script_path}")
        except Exception as e:
            logger.warning(f"Failed to remove temporary script {script_path}: {e}")
        
        return success, output
    
    except Exception as e:
        logger.error(f"Unexpected error executing commands with pkexec script: {e}", exc_info=True)
        error_message = f"Unexpected error: {e}"
        if "authenticate" in str(e).lower() or "cancel" in str(e).lower():
            error_message = translator.get_text("Authentication cancelled or failed.")
        return False, error_message

# Keep get_translator if it's used elsewhere, otherwise it can be removed too
# Keep logger if used elsewhere