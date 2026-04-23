function[stat]=fixmagvar(infile,fixflag)
% load up all the matfiles, either fix the magvar part of 
% meta.platform struct, or remove it
%
% first generate the save command based on what's in the file
scmd=sprintf('save %s ',infile);
finfo=whos ('-file',infile);
for jj=1:length(finfo )
    fn=char(finfo(jj).name);
    scmd=sprintf('%s %s',scmd,fn);
end

% now load it
eval(['load ' infile]);
if fixflag==1 
    % fix the struct if desired
  % meta.platform.magnetic_variation:  [1x1] struct
  % value_to_be_applied:6.8621
  % units:degrees East
  % model:IGRF11
  % url:http://www.ngdc.noaa.gov/geomag-web/#declination
  % run_date:2014/02/18
  % inputs.date_string:37.2963
  % inputs.date:2014.6795
  % inputs.latitude:-19.69
  % inputs.longitude:-85.57
  % inputs.elevation:0
  % change_min_per_year:-6.7849  
    mcinputs=struct('date_string','2014/09/25', 'date',2014.73151,...
        'latitude',-19.6245,   'longitude',-84.9523,   'elevation',0.0);    
    meta.platform.magnetic_variation = struct( 'value_to_be_applied',6.53284,'units', 'degrees East', ...
        'model','IGRF11','version','0.5.0.7','url','http://www.ngdc.noaa.gov/geomag-web/#declination',...
        'run_date','2015/05/15','inputs',mcinputs, 'change_deg_per_year',-0.10847);
    fprintf('%s fixing magnetic variation\n',infile);
    disp(scmd)
    eval(scmd)
else
    % otherwise, remoive it, if it exists
    if isfield(meta.platform,'magnetic_variation')
        meta.platform=rmfield(meta.platform,'magnetic_variation');
        fprintf('%s removing magnetic_variation from meta.platform\n',infile);
        disp(scmd)
        eval(scmd)
    else
        fprintf('%s has no magnetic_variation in meta.platform\n',infile);
    end
end

    
