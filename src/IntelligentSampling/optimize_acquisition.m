function x_next = optimize_acquisition(acq_fun, lb, ub)
    % 使用遗传算法进行全局优化
    obj_fun = @(x) -acq_fun(x);  % 转换为最小化问题
    % lb = x_range(:,1);
    % ub = x_range(:,2);
    options = optimoptions('ga','PopulationSize',30,'MaxGenerations',10,...
                          'Display','off');
    x_next = ga(obj_fun, length(lb), [], [], [], [], lb, ub, [], options);
end