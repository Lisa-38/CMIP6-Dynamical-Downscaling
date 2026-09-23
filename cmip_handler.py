#/usr/bin/env python3
"""Build Observation Station Objects"""

import datetime
import pandas as pd 
import xarray as xr
import numpy as np
from scipy.io import FortranFile
from utils import utils
from scipy.interpolate import griddata

import os


print_prefix='lib.cmip_container>>'

# below for interp constants
# All source data from various models are interpolated to the same mesh.


class CMIPHandler(object):

    '''
    Construct CMIP Handler 

    Methods
    -----------
    __init__:   initialize CMIP Handler with config and loading data
    interp_data: interpolate data to common mesh
    write_wrfinterm: write wrfinterm file

    '''
    
    def __init__(self, cfg):
        '''
        Initialize CMIP Handler with config and load data
        '''
        
        in_cfg=cfg['INPUT']
        out_cfg=cfg['OUTPUT']

        self.model_name=in_cfg['model_name']
        self.scenario=in_cfg['scenario']
        if 'cmip_strt_ts' in in_cfg: # exists
            self.cmip_strt_ts=in_cfg['cmip_strt_ts']
            self.cmip_end_ts=in_cfg['cmip_end_ts']

        self.etl_strt_time=datetime.datetime.strptime(
            out_cfg['etl_strt_ts'],'%Y%m%d%H%M')
        self.etl_end_time=datetime.datetime.strptime(
            out_cfg['etl_end_ts'],'%Y%m%d%H%M')
        self.in_root=in_cfg['input_root']
        self.out_root=out_cfg['output_root']

        self._build_meta(in_cfg)
        self._load_cmip_data()        
        self.out_slab=utils.gen_wrf_mid_template()


    def _build_meta(self, in_cfg):
        '''
        Build metadata for model and scenario
        '''
        df_meta=pd.read_csv('./db/cmip6_meta.csv')
        meta_scenario='ssp' if self.scenario[0:3]=='ssp' else self.scenario  
        tgt_rows=df_meta.loc[
            (df_meta['model_name'] == self.model_name) & (
            df_meta['scenario'] == meta_scenario)]
        if tgt_rows.shape[0] == 0:
            utils.throw_error(
                f'Error: Invalid scenario: {self.scenario} for model {self.model_name}')
        
        self.meta_rows=tgt_rows

        # build file names
        self.fn_lst=[]
        frq='6h'
        for idx, row in tgt_rows.iterrows():
            
            # get main atm_frq
            if '*' in row['var_frq']:
                frq=row['var_frq'].replace('*','')
                self.out_time_series=pd.date_range(
                    start=self.etl_strt_time, end=self.etl_end_time, freq=frq)

            # get file name
            if self.model_name == 'BCMM':
                fn=row['naming_convention'].replace('SCENARIO',self.scenario)
                fn=fn.replace('YYYY',self.etl_strt_time.strftime('%Y'))
                fn=fn.replace('MM',self.etl_strt_time.strftime('%m'))
                # self.fn_lst.append(self.in_root+'/'+fn)
                self.fn_lst.append(os.path.join(self.in_root, fn.strip('/')))
            else:
                # CMIP6 regrular
                vtable_fn=f"{self.model_name}_{row['variable_group']}"
                df_vtable=pd.read_csv('./db/'+vtable_fn+'.csv')
                for idy, itm in df_vtable.iterrows():
                    varname=itm['src_v']
                    lvlmark=itm['lvlmark']
                    
                    self.fn_lst = {
                    "ta": os.path.join(self.in_root, "ta_6h.nc"),
                    "ua": os.path.join(self.in_root, "ua_6h.nc"),
                    "va": os.path.join(self.in_root, "va_6h.nc"),
                    "hus": os.path.join(self.in_root, "hus_6h.nc"),
                    "zg": os.path.join(self.in_root, "zg_6h.nc"),
                    "ps": os.path.join(self.in_root, "ps_6h.nc"), 
                    "tas": os.path.join(self.in_root, "tas_6h.nc"), 
                    "uas": os.path.join(self.in_root, "uas_6h.nc"), 
                    "vas": os.path.join(self.in_root, "vas_6h.nc"), 
                    "huss": os.path.join(self.in_root, "huss_6h.nc"), 
                    "psl": os.path.join(self.in_root, "psl_6h.nc"),
                    "mrsol": os.path.join(self.in_root, "mrsol_final_v2.nc"), #has the right unit unlike mrsol_6h.nc
                    "tsl": os.path.join(self.in_root, "tsl_final_v2.nc"), #trick to match mrsol layers because tsl_6h has one layer only
                    "ts": os.path.join(self.in_root, "ts_6h.nc")
                    }
                    # fn=varname+'_'+frq+'r'+lvlmark+'_'+self.model_name
                    # fn=fn+'_'+self.scenario+'_'+in_cfg['esm_flag']+'_'+in_cfg['grid_flag']
                    # fn+='_'+in_cfg['cmip_strt_ts']+'-'+in_cfg['cmip_end_ts']+'.nc'
                    # self.fn_lst.append(self.in_root+'/'+fn)
    # def _load_cmip_data(self):
    #     '''
    #     Load CMIP data according to file convension
    #     ''' 
    #     # init empty cmip container dict
    #     self.ds, self.outfrm={},{}
    #     idf=0 # file index for CMIP6 files
    #     for idx, irow in self.meta_rows.iterrows():
    #         vtable_fn=f"{self.model_name}_{irow['variable_group']}"
    #         df_vtable=pd.read_csv('./db/'+vtable_fn+'.csv')
    #         if self.model_name=='BCMM':
    #             utils.write_log(print_prefix+'Loading '+self.fn_lst[idx])
    #             # ds=xr.open_dataset(self.fn_lst[idx])
    #             ds = xr.open_dataset(self.fn_lst[idf], engine='netcdf4')
    #         for idy, itm in df_vtable.iterrows():
    #             varname=itm['src_v']
    #             lvlmark=itm['lvlmark']
    #             if lvlmark == 'None':
    #                 lvlmark=''
                
    #             # repeated usage in vtable will not be reloaded
    #             if varname in self.ds:
    #                 continue
                
    #             # CMIP6 regular
    #             if not(self.model_name=='BCMM'):
    #                 utils.write_log(print_prefix+'Loading '+self.fn_lst[idx])
    #                 ds=xr.open_dataset(self.fn_lst[idf])
    #                 idf=idf+1
                    
    #             # need interpolation coefficients
    #             if (lvlmark=='Lev' and itm['type']=='3d'):
    #                 if not(hasattr(self,'ap')):
    #                     self.ap=ds['ap'].values
    #                     self.b=ds['b'].values
    #                     self.ps=ds['ps'].sel(
    #                     time=slice(self.etl_strt_time,self.etl_end_time))

    #             # special for BCMM
    #             if (self.model_name=='BCMM' and irow['var_frq'] =='1M'): 
    #                 self.ds[varname]=ds[varname]
    #             else:
    #                 self.ds[varname]=ds[varname].sel(
    #                     time=slice(self.etl_strt_time,self.etl_end_time))
                
    #             # unify vertical layers naming 
    #             if (lvlmark=='PlevPt' and itm['type']=='3d'):
    #                 if 'lev' in self.ds[varname].coords:
    #                     self.ds[varname] = self.ds[varname].rename({'lev': 'plev'})
    #             if not(self.model_name=='BCMM'):
    #                 ds.close()
    #         if self.model_name=='BCMM':
    #             ds.close()
    
    def _load_cmip_data(self):
    # """
    # Load CMIP data from manually specified files
    # """
        self.ds = {}
        self.outfrm = {}

        for varname, filepath in self.fn_lst.items():
            utils.write_log(print_prefix + f"Loading {filepath}")

            ds = xr.open_dataset(filepath, engine="netcdf4")

            # time slice
            da = ds[varname].sel(
            time=slice(self.etl_strt_time, self.etl_end_time)
            )

            self.ds[varname] = da

            # load hybrid coefficients if present
            if 'ap' in ds.variables and not hasattr(self, 'ap'):
                self.ap = ds['ap'].values
                self.b = ds['b'].values
                self.ps = ds['ps'].sel(
                time=slice(self.etl_strt_time, self.etl_end_time)
                )

            ds.close()


    def parse_data(self, tf):
        '''
        data parser before write to WRF-Interim, including but not limited to:
            1. Interpolating to common mesh
            2. Dealing with missing values
            3. Converting Units 
        '''
        for idx, irow in self.meta_rows.iterrows():

            vtable_fn = f"{self.model_name}_{irow['variable_group']}"
            df_vtable = pd.read_csv('./db/' + vtable_fn + '.csv')

            for idy, itm in df_vtable.iterrows():
                varname = itm['src_v']
                lvltype = itm['type']
                lvlmark = itm['lvlmark']
                utils.write_log(
                    print_prefix + 'Parsing ' + varname + ',lvltype=' + lvltype + ',lvlmark=' + lvlmark
                )




                # ADD THIS LINE HERE:
                if varname == 'PRES': continue
                
                # special for BCMM
                if (self.model_name == 'BCMM' and irow['var_frq'] == '1M'):
                    da = self.ds[varname]
                else:
                    da = self.ds[varname].sel(time=tf, method='nearest')

                print(f"{varname} input NaNs: {np.isnan(da.values).sum()}")

                # units conversion, if necessary
                if varname == 'mrsol' and itm['units'] == 'kg m-2':
                # This is a simplified conversion: mass / (density_water * thickness)
                # Most people use a representative density of 1000 kg/m3.
                # If your input is total mass in the layer, you must divide by thickness.
                    thicknesses = np.array([0.065, 0.254, 0.913, 2.85, 5.70])
                    # We apply this along the 'plev' axis
                    da.values = da.values / (1000.0 * thicknesses[:, None, None])
                    itm['units'] = 'm3 m-3'
                
                if varname == 'mrsos' and itm['units'] == 'kg/m-3':
                    da.values = da.values * 1e-2  # m^3/m^3

                if varname == 'tos' and itm['units'] == 'degC':
                    da.values = da.values + 273.15
                    itm['units'] = 'K'

                if lvltype == '3d':
                    
                    if varname in ['tsl', 'mrsol', 'ST', 'SM']:
                        # For soil, just interpolate horizontally, skip vertical hybrid math
                        tmp = da.interp(
                            lat=utils.LATS, 
                            lon=utils.LONS, 
                            method='linear',
                            kwargs={"fill_value": "extrapolate"}
                            )
                        tmp = tmp.ffill("lat").bfill("lat").ffill("lon").bfill("lon")
                        
                        self.outfrm[varname] = tmp
                    else: 
                        if lvlmark == 'Lev':
                            da = utils.hybrid2pressure(
                            da, self.ap, self.b, self.ps.sel(time=tf, method='nearest')
                            )

                        
                        if varname in ['zg', 'GHT']:
                            # Sort plev to be increasing for interpolation
                            da = da.sortby("plev") 
                            da = da.interpolate_na(dim="plev", method="linear", fill_value="extrapolate")
                            # Optional: sort back to your original preferred order if needed
                            # da = da.sortby("plev", ascending=False) 
                        else:
                            da = da.ffill("plev").bfill("plev")

                        tmp = da.interp(
                            lat=utils.LATS,
                            lon=utils.LONS,
                            plev=utils.PLVS,
                            method='linear',
                            kwargs={"fill_value": "extrapolate"}
                        )

                        print(f"{varname} after interp NaNs: {np.isnan(tmp.values).sum()}")

                        self.outfrm[varname] = tmp
                    
                    
                # if lvltype == '3d':
                #     if lvlmark == 'Lev':
                #         # interpolate from hybrid to pressure level
                #         da = utils.hybrid2pressure(
                #             da, self.ap, self.b, self.ps.sel(time=tf, method='nearest')
                #         )
                #         print(f"{varname} after hybrid2pressure NaNs: {np.isnan(da.values).sum()}")

                #     tmp = da.interp(
                #         lat=utils.LATS,
                #         lon=utils.LONS,
                #         plev=utils.PLVS,
                #         method='linear',
                #         kwargs={"fill_value": "extrapolate"}
                #     )

                #     print(f"{varname} after interp NaNs: {np.isnan(tmp.values).sum()}")

                #     self.outfrm[varname] = tmp

                elif lvltype in ['2d', '2d-soil']:
                    da = da.interpolate_na(
                        dim="lon", method="linear", fill_value="extrapolate"
                    )

                    tmp = da.interp(
                            lat=utils.LATS,
                            lon=utils.LONS,
                            method='linear',
                            kwargs={"fill_value": "extrapolate"}
                        )
                    self.outfrm[varname] = tmp

                print(f"{varname} after interp NaNs: {np.isnan(tmp.values).sum()}")
                

                # self.outfrm[varname] = tmp

    # def parse_data(self, tf):
    #     '''
    #     data parser before write to WRF-Interim, including but not limited to:
    #         1. Interpolating to common mesh
    #         2. Dealing with missing values
    #         3. Converting Units 
    #     '''
    #     for idx, irow in self.meta_rows.iterrows():
            
    #         vtable_fn=f"{self.model_name}_{irow['variable_group']}"
    #         df_vtable=pd.read_csv('./db/'+vtable_fn+'.csv')
            
    #         for idy, itm in df_vtable.iterrows():
    #             varname=itm['src_v']
    #             lvltype=itm['type']
    #             lvlmark=itm['lvlmark']
    #             utils.write_log(
    #                 print_prefix+'Parsing '+varname+',lvltype='+lvltype+',lvlmark='+lvlmark)
                
    #             # special for BCMM
    #             if (self.model_name=='BCMM' and irow['var_frq'] =='1M'): 
    #                 da=self.ds[varname]
    #             else:
    #                 da=self.ds[varname].sel(time=tf, method='nearest')
    #                 #### added
    #                 print(f"{varname} input NaNs:", np.isnan(da.values).sum())
                
    #             # units conversion, if necessary
    #             if varname =='mrsos' and itm['units']=='kg/m-3':
    #                 da.values=da.values*1e-2 # m^3/m-3
    #             if varname =='tos' and itm['units']=='degC':
    #                 da.values=da.values+273.15
    #                 itm['units']='K'

    #             if lvltype=='3d':
    #                 if lvlmark == 'Lev':
    #                     # interpolate from hybrid to pressure level 
    #                     da=utils.hybrid2pressure(
    #                         da,self.ap,self.b,self.ps.sel(time=tf, method='nearest'))
    #                 self.outfrm[varname]=da.interp(lat=utils.LATS, lon=utils.LONS, plev=utils.PLVS,
    #                         method='linear',kwargs={"fill_value": "extrapolate"})
    #                 ### added
    #                 if lvlmark == 'Lev':
    #                     da=utils.hybrid2pressure(
    #                     da,self.ap,self.b,self.ps.sel(time=tf, method='nearest'))
    #                     print(f"{varname} after hybrid2pressure NaNs:", np.isnan(da.values).sum())

                    
    #             elif lvltype in ['2d', '2d-soil']:
    #                 da=da.interpolate_na(
    #                     dim="lon", method="linear",fill_value="extrapolate")    
    #                 self.outfrm[varname]=da.interp(lat=utils.LATS, lon=utils.LONS,
    #                     method='linear',kwargs={"fill_value": "extrapolate"})
    #             '''
    #             elif lvltype=='ocn2d':
    #                 ocn_da=da.interpolate_na(dim='i',
    #                     method='linear',fill_value="extrapolate")
    #                 ocn_da=ocn_da.interpolate_na(dim='j',
    #                     method='linear',fill_value="extrapolate")
    #                 grid_x,grid_y=np.meshgrid(new_lon,new_lat)
    #                 values=ocn_da.values
    #                 points=np.array(
    #                     [da.longitude.values.flatten(),da.latitude.values.flatten()]).T
    #                 # here use nearest as linear will cause some nan
    #                 grid_z0 = griddata(
    #                     points, values.flatten(), 
    #                     (grid_x, grid_y), method='nearest')  
    #                 self.outfrm[varname]=grid_z0
    #             '''
    
    def write_wrfinterm(self, tf, tgt):
        if tgt == 'main':
            out_fn = os.path.join(self.out_root, self.model_name + ':' + tf.strftime('%Y-%m-%d_%H'))
        elif tgt == 'sst':
            out_fn = os.path.join(self.out_root, self.model_name + '_SST:' + tf.strftime('%Y-%m-%d_%H'))
        
        utils.write_log(print_prefix + 'Writing ' + out_fn)
        # dtype='>u4' for big-endian header
        wrf_mid = FortranFile(out_fn, 'w', header_dtype=np.dtype('>u4'))
        
        out_dic = self.out_slab
        out_dic['HDATE'] = tf.strftime('%Y-%m-%d_%H:%M:%S:0000')
        
        for idx, irow in self.meta_rows.iterrows():
            # Re-define the Vtable for the current group
            vtable_fn = f"{self.model_name}_{irow['variable_group']}"
            df_vtable = pd.read_csv('./db/' + vtable_fn + '.csv')
            
            for idy, itm in df_vtable.iterrows():
                if (tgt == 'sst' and itm['aim_v'] != 'SST'):
                    continue
                
                varname = itm['src_v']
                
                if varname == 'PRES': continue
                
                lvltype = itm['type']
                
                # Metadata setup
                out_dic['FIELD'] = itm['aim_v']
                out_dic['UNIT'] = itm['units']
                out_dic['DESC'] = itm['desc']
                
                # Logic for 3D variables (TT, UU, VV, GHT, SPECHUMD)
                if lvltype == '3d':
                    if varname in ['tsl', 'mrsol', 'ST', 'SM']:
                        # --- SOIL PATH ---
                        soil_depths = {0: "000010", 1: "010040", 2: "040100", 3: "100200", 4: "100200"}
                        
                        base_name = itm['aim_v'] # This is 'ST' or 'SM' from your Vtable
                        
                        for i, lvl in enumerate(self.outfrm[varname].plev.values):
                            if i >= 4: break # Most WRF setups only use 4 layers
                            
                            # 1. Change the Field Name to include depth (e.g., ST + 000010)
                            out_dic['FIELD'] = f"{base_name}{soil_depths[i]}"
                            
                            # 2. Set XLVL to the "Surface/Soil" code Metgrid expects
                            out_dic['XLVL'] = 200100.0
                            
                            # 3. Extract and write
                            out_dic['SLAB'] = self.outfrm[varname].sel(plev=lvl, method='nearest').values.astype('>f4').squeeze()
                            utils.write_record(wrf_mid, out_dic)
                        
                        # Reset FIELD name for the next iteration of the loop
                        out_dic['FIELD'] = base_name
                        
                    else:
                    
                        for lvl in utils.PLVS:
                            out_dic['XLVL'] = float(lvl)
                            # Extract the slab for the specific pressure level
                            out_dic['SLAB'] = self.outfrm[varname].sel(plev=lvl).values.astype('>f4').squeeze()
                            utils.write_record(wrf_mid, out_dic)
                
                    # Logic for 2D variables (PSFC, T2, Q2, PMSL, etc)
                elif lvltype in ['2d', '2d-soil']:
                    out_dic['XLVL'] = 200100.0
                    
                    if lvltype == '2d-soil':
                        index = next((i for i, s in enumerate(utils.SOIL_LVS) if s in itm['aim_v']), None)
                        if self.model_name == 'BCMM':
                                out_dic['SLAB'] = self.outfrm[varname].values[:, index, :, :].astype('>f4').squeeze()
                        else:
                                out_dic['SLAB'] = self.outfrm[varname].values.astype('>f4').squeeze()
                    else:
                            # Standard 2D
                        out_dic['SLAB'] = self.outfrm[varname].values.astype('>f4').squeeze()

                    utils.write_record(wrf_mid, out_dic)
        
        
        # 2. THE PRESSURE INJECTION (Ensures PRES is always there)
        if tgt == 'main':
            out_dic['FIELD'] = 'PRES'
            out_dic['UNIT'] = 'Pa'
            out_dic['DESC'] = '3D Pressure Field'
            for lvl in utils.PLVS:
                out_dic['XLVL'] = float(lvl)
                out_dic['SLAB'] = np.full((len(utils.LATS), len(utils.LONS)), 
                                          float(lvl), dtype='>f4').squeeze()
                
                print(f"DEBUG: Writing {out_dic['FIELD']} at {out_dic['XLVL']} with shape {out_dic['SLAB'].shape}")
                
                utils.write_record(wrf_mid, out_dic)    
                    
        wrf_mid.close()
    
    
    
    # def write_wrfinterm(self, tf, tgt):
    #     if tgt=='main':
    #         out_fn=self.out_root+'/'+self.model_name+':'+tf.strftime('%Y-%m-%d_%H')
    #     if tgt=='sst':
    #         out_fn=self.out_root+'/'+self.model_name+'_SST:'+tf.strftime('%Y-%m-%d_%H')
        
    #     utils.write_log(print_prefix+'Writing '+out_fn)
    #     # dtype='>u4' for header (big-endian, unsigned int)
    #     wrf_mid = FortranFile(out_fn, 'w', header_dtype=np.dtype('>u4'))
        
    #     out_dic=self.out_slab
    #     out_dic['HDATE']=tf.strftime('%Y-%m-%d_%H:%M:%S:0000')
        
    #     for idx, irow in self.meta_rows.iterrows():
            
    #         vtable_fn=f"{self.model_name}_{irow['variable_group']}"
    #         df_vtable=pd.read_csv('./db/'+vtable_fn+'.csv')
            
    #         for idy, itm in df_vtable.iterrows():
    #             if (tgt == 'sst' and itm['aim_v'] != 'SST'):
    #                 continue
    #             varname=itm['src_v']
    #             lvltype=itm['type']
    #             out_dic['FIELD']=itm['aim_v']
    #             out_dic['UNIT']=itm['units']
    #             out_dic['DESC']=itm['desc']
    #             out_dic['XLVL']=200100.0
                
    #             if varname=='tos':
    #                 out_dic['UNIT']='K'
                
    #             if lvltype=='3d':
    #                 for lvl in utils.PLVS:
    #                     out_dic['XLVL']=lvl
    #                     out_dic['SLAB']=self.outfrm[varname].sel(plev=lvl).values
    #                     utils.write_record(wrf_mid, out_dic)
    #             elif lvltype=='2d':
    #                 # use the lowest level if no direct output
    #                 #if varname=='tos':
    #                 #    out_dic['SLAB']=self.outfrm[varname]
    #                 if varname in ['ta', 'ua', 'va', 'hur', 'hus']:
    #                     out_dic['SLAB']=self.outfrm[varname].sel(plev=100000.0).values
    #                 else: 
    #                     out_dic['SLAB']=self.outfrm[varname].values
    #             elif lvltype=='2d-soil':
    #                 index = next(
    #                     (i for i, s in enumerate(utils.SOIL_LVS) if s in itm['aim_v']), None)
    #                 if self.model_name == 'BCMM':
    #                     out_dic['SLAB']=self.outfrm[varname].values[:,index,:,:]
    #                 else:
    #                     out_dic['SLAB']=self.outfrm[varname].values

    #             utils.write_record(wrf_mid, out_dic)
    #     wrf_mid.close()


if __name__ == "__main__":
    pass
