# frozen_string_literal: true
require 'bundler/setup'
require "aws-sdk-dynamodb"

class ItemNotFoundError < StandardError; end

def lambda_handler(event:, context:)
  id = event["pathParameters"]["id"]
  item = client.get_item(
    table_name: ENV["RUBY_LAMBDA_TABLE"],
    key: { "id" => id }
  ).item

  raise ItemNotFoundError if item.nil?

  client.delete_item(
    table_name: ENV["RUBY_LAMBDA_TABLE"],
    key: { "id" => id }
  )

  { statusCode: 204 }
rescue ItemNotFoundError
  { statusCode: 404, body: { error: "Item #{id} not found" }.to_json }
end

def client
  @client ||= Aws::DynamoDB::Client.new
end
