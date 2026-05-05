
help([[
sgeconvert 0.1.0: CLI tool to convert SGE to SLURM

The following environment variables are provided for convenience:
$SCC_SCC_SGECONVERT_BASE -- Package Base Directory
$SCC_SGECONVERT_DIR -- Package Install Directory
$SCC_SGECONVERT_BIN -- Package Executables Directory
--$SCC_SGECONVERT_LIB -- Package Libraries Directory
--$SCC_SGECONVERT_INCLUDE -- Package Headers Directory
--$SCC_SGECONVERT_DATA -- Package Data Directory
--$SCC_SGECONVERT_EXAMPLES -- Package Examples Directory
--$SCC_SGECONVERT_LICENSE -- Package License Information
  
]])
--NOTES: categories and keywords should be all lowercase. 
whatis("Name:         " .. myModuleName())
whatis("Version:      " .. myModuleVersion())
whatis("Categories:   utilities")
whatis("Keywords:     alma8, utilities, scc")
whatis("URL:          https://github.com/Ryan-J-Gilbert/sge-to-slurm")
whatis("Description:  CLI tool to convert SGE to SLURM")
-- base is the SCC_SGECONVERT_BASE location
local base = pathJoin("/share/pkg.8",myModuleName(),myModuleVersion())
setenv("SCC_SGECONVERT_BASE",      base)
setenv("SGE_TO_SLURM_CONFIG",      pathJoin(base,"sge_to_slurm.scc.yaml"))
-- now append /install for consistency with past modulefiles 
base = pathJoin(base,"install")

setenv("SCC_SGECONVERT_DIR",      base)
setenv("SCC_SGECONVERT_BIN",      pathJoin(base,"bin"))
--setenv("SCC_SGECONVERT_LIB",      pathJoin(base,"lib"))
--setenv("SCC_SGECONVERT_INCLUDE",  pathJoin(base,"include"))
--setenv("SCC_SGECONVERT_DATA",     pathJoin(base,"data"))
--setenv("SCC_SGECONVERT_EXAMPLES", pathJoin(base,"share","examples"))
--setenv("SCC_SGECONVERT_LICENSE",  pathJoin(base,"license"))
prepend_path("PATH",pathJoin(base,"bin"))
--prepend_path("CMAKE_PREFIX_PATH",base)
--prepend_path("LD_LIBRARY_PATH",pathJoin(base,"lib"))
--prepend_path("PKG_CONFIG_PATH",pathJoin(base,"lib","pkgconfig"))
