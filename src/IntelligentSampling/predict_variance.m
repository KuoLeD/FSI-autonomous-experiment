function var = predict_variance(model, x, w_mu, w_sigma) 
    [ymu, ysd,~ ] = predict(model, x);
    var = w_mu * ymu + w_sigma * ysd.^2;  % 直接返回预测方差
end